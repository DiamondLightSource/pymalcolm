import unittest

from malcolm.core import Process, Post, Subscribe, Return, \
    Update, Controller, Queue, TimeoutError
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
        sub = Subscribe(id=20, path=["counting", "counter"], delta=False)
        sub.set_callback(q.put)
        self.controller.handle_request(sub)
        response = q.get(timeout=1.0)
        self.assertIsInstance(response, Update)
        assert response.id == 20
        assert response.value["typeid"] == "epics:nt/NTScalar:1.0"
        assert response.value["value"] == 0
        post = Post(id=21, path=["counting", "increment"])
        post.set_callback(q.put)
        self.controller.handle_request(post)
        response = q.get(timeout=1)
        self.assertIsInstance(response, Update)
        assert response.id == 20
        assert response.value["value"] == 1
        response = q.get(timeout=1)
        self.assertIsInstance(response, Return)
        assert response.id == 21
        assert response.value is None
        with self.assertRaises(TimeoutError):
            q.get(timeout=0.05)
