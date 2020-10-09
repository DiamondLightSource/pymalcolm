import unittest

from malcolm.core import (
    Alarm,
    Controller,
    Delta,
    Error,
    Post,
    Process,
    Put,
    Queue,
    Return,
    Subscribe,
    TimeoutError,
    Update,
)
from malcolm.modules.demo.parts import CounterPart, HelloPart


class TestHelloDemoSystem(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.controller = Controller("hello_block")
        self.controller.add_part(HelloPart("hpart"))
        self.process.add_controller(self.controller)
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_hello_good_input(self):
        q = Queue()
        request = Post(
            id=44, path=["hello_block", "greet"], parameters=dict(name="thing")
        )
        request.set_callback(q.put)
        self.controller.handle_request(request)
        response = q.get(timeout=1.0)
        self.assertIsInstance(response, Return)
        assert response.id == 44
        assert response.value == "Hello thing"

    def test_concurrent(self):
        q = Queue()
        request = Subscribe(id=40, path=["hello_block", "greet"], delta=True)
        request.set_callback(q.put)
        self.controller.handle_request(request)
        # Get the initial subscribe value
        inital = q.get(timeout=0.1)
        self.assertIsInstance(inital, Delta)
        assert inital.changes[0][1]["took"]["value"] == dict(sleep=0, name="")
        assert inital.changes[0][1]["returned"]["value"] == {"return": ""}
        # Do a greet
        request = Post(
            id=44, path=["hello_block", "greet"], parameters=dict(name="me", sleep=1)
        )
        request.set_callback(q.put)
        self.controller.handle_request(request)
        # Then an error
        request = Post(id=45, path=["hello_block", "error"])
        request.set_callback(q.put)
        self.controller.handle_request(request)
        # We should quickly get the error response first
        response = q.get(timeout=1.0)
        self.assertIsInstance(response, Error)
        assert response.id == 45
        # Then the long running greet delta
        response = q.get(timeout=3.0)
        self.assertIsInstance(response, Delta)
        assert len(response.changes) == 2
        assert response.changes[0][0] == ["took"]
        took = response.changes[0][1]
        assert took.value == dict(sleep=1, name="me")
        assert took.present == ["name", "sleep"]
        assert took.alarm == Alarm.ok
        assert response.changes[1][0] == ["returned"]
        returned = response.changes[1][1]
        assert returned.value == {"return": "Hello me"}
        assert returned.present == ["return"]
        assert returned.alarm == Alarm.ok
        # Check it took about 1s to run
        assert abs(1 - (returned.timeStamp.to_time() - took.timeStamp.to_time())) < 0.4
        # And it's response
        response = q.get(timeout=1.0)
        self.assertIsInstance(response, Return)
        assert response.id == 44
        assert response.value == "Hello me"


class TestCounterDemoSystem(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.controller = Controller("counting")
        self.controller.add_part(CounterPart("cpart"))
        self.process.add_controller(self.controller)
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_counter_subscribe(self):
        q = Queue()
        # Subscribe to the value
        sub = Subscribe(id=20, path=["counting", "counter"], delta=False)
        sub.set_callback(q.put)
        self.controller.handle_request(sub)
        # Check initial return
        response = q.get(timeout=1.0)
        self.assertIsInstance(response, Update)
        assert response.id == 20
        assert response.value["typeid"] == "epics:nt/NTScalar:1.0"
        assert response.value["value"] == 0
        # Post increment()
        post = Post(id=21, path=["counting", "increment"])
        post.set_callback(q.put)
        self.controller.handle_request(post)
        # Check the value updates...
        response = q.get(timeout=1)
        self.assertIsInstance(response, Update)
        assert response.id == 20
        assert response.value["value"] == 1
        # ... then we get the return
        response = q.get(timeout=1)
        self.assertIsInstance(response, Return)
        assert response.id == 21
        assert response.value is None
        # Check we can put too
        put = Put(id=22, path=["counting", "counter", "value"], value=31)
        put.set_callback(q.put)
        self.controller.handle_request(put)
        # Check the value updates...
        response = q.get(timeout=1)
        self.assertIsInstance(response, Update)
        assert response.id == 20
        assert response.value["value"] == 31
        # ... then we get the return
        response = q.get(timeout=1)
        self.assertIsInstance(response, Return)
        assert response.id == 22
        assert response.value is None
        # And that there isn't anything else
        with self.assertRaises(TimeoutError):
            q.get(timeout=0.05)
