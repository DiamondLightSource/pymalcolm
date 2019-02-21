import unittest

from malcolm.core import Process, Post, Subscribe, Return, \
    Update, Controller, Queue, TimeoutError, Put, Error, Delta, TimeStamp
from malcolm.modules.demo.parts import HelloPart, CounterPart


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
        request = Post(id=44, path=["hello_block", "greet"],
                       parameters=dict(name="thing"))
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
        assert inital.changes[0][1]["took"]["value"] == dict(sleep=0, name='')
        assert inital.changes[0][1]["returned"]["value"] == {'return': ''}
        # Do a greet
        request = Post(id=44, path=["hello_block", "greet"],
                       parameters=dict(name="me", sleep=1))
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
        assert len(response.changes) == 7
        assert response.changes[0][0] == ["took", "value"]
        assert response.changes[0][1] == dict(sleep=1, name="me")

        assert response.changes[1][0] == ["took", "present"]
        assert response.changes[1][1] == ["name", "sleep"]

        assert response.changes[2][0] == ["took", "timeStamp"]

        assert response.changes[3][0] == ["returned", "value"]
        assert response.changes[3][1] == {"return": "Hello me"}

        assert response.changes[4][0] == ["returned", "present"]
        assert response.changes[4][1] == ["return"]

        assert response.changes[5][0] == ["returned", "alarm"]
        assert response.changes[5][1]["severity"] == 0

        assert response.changes[6][0] == ["returned", "timeStamp"]

        took_ts = TimeStamp.from_dict(response.changes[2][1])
        returned_ts = TimeStamp.from_dict(response.changes[6][1])
        # Check it took about 1s to run
        assert abs(1 - (returned_ts.to_time() - took_ts.to_time())) < 0.4
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

