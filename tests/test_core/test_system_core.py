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
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core.ntscalar import NTScalar
from malcolm.core.process import Process
from malcolm.core.syncfactory import SyncFactory
from malcolm.core.request import Post, Subscribe
from malcolm.core.response import Return, Update
from malcolm.core.task import Task
from malcolm.parts.demo import HelloPart, CounterPart


class TestHelloDemoSystem(unittest.TestCase):

    def test_hello_good_input(self):
        p = MagicMock()
        part = HelloPart(p, None)
        block = DefaultController("hello", p, parts={"hello":part}).block
        block.reset()
        result = block.say_hello(name="me")
        self.assertEquals(result.greeting, "Hello me")

    def test_hello_with_process(self):
        sync_factory = SyncFactory("sched")
        process = Process("proc", sync_factory)
        part = HelloPart(process, None)
        b = DefaultController("hello", process, parts={"hello":part}).block
        process.start()
        # wait until block is Ready
        task = Task("hello_ready_task", process)
        futures = task.when_matches(b["state"], "Ready")
        task.wait_all(futures, timeout=1)
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


class TestCounterDemoSystem(unittest.TestCase):

    def test_counter_subscribe(self):
        sync_factory = SyncFactory("sched")
        process = Process("proc", sync_factory)
        part = CounterPart(process, None)
        b = DefaultController("counting", process, parts={"counter":part}).block
        process.start()
        # wait until block is Ready
        task = Task("counter_ready_task", process)
        futures = task.when_matches(b["state"], "Ready")
        task.wait_all(futures, timeout=1)
        q = sync_factory.create_queue()

        sub = Subscribe(response_queue=q, context="ClientConnection",
                        endpoint=["counting", "counter"],
                        delta=False)
        process.q.put(sub)
        resp = q.get(timeout=1)
        self.assertIsInstance(resp, Update)
        attr = NTScalar.from_dict(resp.value)
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
