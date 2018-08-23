import unittest

from malcolm.core import Process, Post, Subscribe, Return, \
    Update, Controller, Queue, TimeoutError, Put
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

