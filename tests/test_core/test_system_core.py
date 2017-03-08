import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import unittest
from mock import MagicMock

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core.ntscalar import NTScalar
from malcolm.core.process import Process
from malcolm.core.request import Post, Subscribe
from malcolm.core.response import Return, Update
from malcolm.core.controller import Controller
from malcolm.core.queue import Queue
from malcolm.core.errors import TimeoutError
from malcolm.parts.demo.hellopart import HelloPart
from malcolm.parts.demo.counterpart import CounterPart


class TestHelloDemoSystem(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        parts = [HelloPart(self.process, "hpart")]
        self.controller = Controller(self.process, "hello", parts)
        self.process.start()

    def tearDown(self):
        self.process.stop()

    def test_hello_good_input(self):
        q = Queue()
        request = Post(id=44, path=["hello", "greet"],
                       parameters=dict(name="thing"), callback=q.put)
        self.controller.handle_request(request)
        response = q.get(timeout=1.0)
        self.assertIsInstance(response, Return)
        self.assertEqual(response.id, 44)
        self.assertEqual(response.value["greeting"], "Hello thing")


class TestCounterDemoSystem(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        parts = [CounterPart(self.process, "cpart")]
        self.controller = Controller(self.process, "counting", parts)
        self.process.start()

    def tearDown(self):
        self.process.stop()

    def test_counter_subscribe(self):
        q = Queue()
        sub = Subscribe(id=20, path=["counting", "counter"], delta=False,
                        callback=q.put)
        self.controller.handle_request(sub)
        response = q.get(timeout=1.0)
        self.assertIsInstance(response, Update)
        self.assertEqual(response.id, 20)
        self.assertEqual(response.value["typeid"], "epics:nt/NTScalar:1.0")
        self.assertEqual(response.value["value"], 0)
        post = Post(id=21, path=["counting", "increment"], callback=q.put)
        self.controller.handle_request(post)
        response = q.get(timeout=1)
        self.assertIsInstance(response, Update)
        self.assertEqual(response.id, 20)
        self.assertEqual(response.value["value"], 1)
        response = q.get(timeout=1)
        self.assertIsInstance(response, Return)
        self.assertEqual(response.id, 21)
        self.assertEqual(response.value, None)
        with self.assertRaises(TimeoutError):
            q.get(timeout=0.05)

if __name__ == "__main__":
    unittest.main(verbosity=2)
