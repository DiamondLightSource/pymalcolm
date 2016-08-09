import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.controllers.hellocontroller import HelloController
from malcolm.controllers.countercontroller import CounterController
from malcolm.core.attribute import Attribute
from malcolm.core.block import Block
from malcolm.core.process import Process
from malcolm.core.syncfactory import SyncFactory
from malcolm.core.request import Post, Subscribe
from malcolm.core.response import Return, Update


class TestHelloControllerSystem(unittest.TestCase):

    def test_hello_controller_good_input(self):
        block = HelloController("hello", MagicMock()).block
        block.reset()
        result = block.say_hello(name="me")
        self.assertEquals(result.greeting, "Hello me")

    def test_hello_controller_with_process(self):
        sync_factory = SyncFactory("sched")
        process = Process("proc", sync_factory)
        HelloController("hello", process)
        process.start()
        q = sync_factory.create_queue()
        req = Post(response_queue=q, context="ClientConnection",
                   endpoint=["hello", "say_hello"],
                   parameters=dict(name="thing"))
        req.set_id(44)
        process.q.put(req)
        resp = q.get(timeout=1)
        self.assertEqual(resp.id, 44)
        self.assertEqual(resp.context, "ClientConnection")
        self.assertEqual(resp.typeid, "malcolm:core/Return:1.0")
        self.assertEqual(resp.value["greeting"], "Hello thing")
        process.stop()


class TestCounterControllerSystem(unittest.TestCase):

    def test_counter_controller_subscribe(self):
        sync_factory = SyncFactory("sched")
        process = Process("proc", sync_factory)
        CounterController("counting", process)
        process.start()
        q = sync_factory.create_queue()

        sub = Subscribe(response_queue=q, context="ClientConnection",
                        endpoint=["counting", "counter"],
                        delta=False)
        process.q.put(sub)
        resp = q.get(timeout=1)
        self.assertIsInstance(resp, Update)
        attr = Attribute.from_dict(resp.value)
        self.assertEqual(0, attr.value)

        post = Post(response_queue=q, context="ClientConnection",
                    endpoint=["counting", "increment"])
        process.q.put(post)

        resp = q.get(timeout=1)
        self.assertIsInstance(resp, Update)
        self.assertEqual(resp.value["value"], 1)
        resp = q.get(timeout=1)
        self.assertIsInstance(resp, Return)

        process.stop()

if __name__ == "__main__":
    unittest.main(verbosity=2)
