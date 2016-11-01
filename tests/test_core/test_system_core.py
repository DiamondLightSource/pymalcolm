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
from malcolm.blocks.demo import Hello, Counter


class TestHelloDemoSystem(unittest.TestCase):

    def test_hello_good_input(self):
        p = MagicMock()
        block = Hello(p, dict(mri="hello"))[0]
        block.reset()
        result = block.greet(name="me")
        self.assertEquals(result.greeting, "Hello me")

    def test_hello_with_process(self):
        sync_factory = SyncFactory("sched")
        process = Process("proc", sync_factory)
        b = Hello(process, dict(mri="hello"))[0]
        process.start()
        # wait until block is Ready
        task = Task("hello_ready_task", process)
        futures = task.when_matches_async(b["state"], "Ready")
        task.wait_all(futures, timeout=1)
        q = sync_factory.create_queue()
        req = Post(response_queue=q, context="ClientConnection",
                   endpoint=["hello", "greet"],
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
        b = Counter(process, dict(mri="counting"))[0]
        process.start()
        # wait until block is Ready
        task = Task("counter_ready_task", process)
        task.when_matches(b["state"], "Ready", timeout=1)
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
