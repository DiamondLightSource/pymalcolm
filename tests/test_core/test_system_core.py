import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import unittest

import logging
logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core import call_with_params, Process, Post, Subscribe, Return, \
    Update, Controller, Queue, TimeoutError
from malcolm.parts.demo.hellopart import HelloPart
from malcolm.parts.demo.counterpart import CounterPart


class TestHelloDemoSystem(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        parts = [call_with_params(HelloPart, name="hpart")]
        self.controller = Controller(self.process, "hello_block", parts)
        self.process.start()

    def tearDown(self):
        self.process.stop()

    def test_hello_good_input(self):
        q = Queue()
        request = Post(id=44, path=["hello_block", "greet"],
                       parameters=dict(name="thing"), callback=q.put)
        self.controller.handle_request(request)
        response = q.get(timeout=1.0)
        self.assertIsInstance(response, Return)
        self.assertEqual(response.id, 44)
        self.assertEqual(response.value["greeting"], "Hello thing")


class TestCounterDemoSystem(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        parts = [call_with_params(CounterPart, name="cpart")]
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
