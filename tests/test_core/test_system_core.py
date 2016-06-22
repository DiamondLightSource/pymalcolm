import unittest

from . import util

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
from malcolm.core.request import Request
from malcolm.core.response import Response


class TestHelloControllerSystem(unittest.TestCase):

    def test_hello_controller_good_input(self):
        block = Block("hello")
        HelloController(block)
        result = block.say_hello(name="me")
        self.assertEquals(result["greeting"], "Hello me")

    def test_hello_controller_with_process(self):
        sync_factory = SyncFactory("sched")
        process = Process("proc", sync_factory)
        block = Block("hello")
        HelloController(block)
        process.add_block(block)
        process.start()
        q = sync_factory.create_queue()
        req = Request.Post(response_queue=q, context="ClientConnection",
                           endpoint=["hello", "say_hello"],
                           parameters=dict(name="thing"))
        req.set_id(44)
        process.q.put(req)
        resp = q.get(timeout=1)
        self.assertEqual(resp.id_, 44)
        self.assertEqual(resp.context, "ClientConnection")
        self.assertEqual(resp.type_, "Return")
        self.assertEqual(resp.value, dict(greeting="Hello thing"))

class TestCounterControllerSystem(unittest.TestCase):

    def test_counter_controller_subscribe(self):
        sync_factory = SyncFactory("sched")
        process = Process("proc", sync_factory)
        block = Block("counting")
        CounterController(block)
        process.add_block(block)
        process.start()
        q = sync_factory.create_queue()

        sub = Request.Subscribe(response_queue=q, context="ClientConnection",
                                endpoint=["counting", "counter"], delta=False)
        process.q.put(sub)
        resp = q.get(timeout=1)
        self.assertEqual(Response.UPDATE, resp.type_)
        attr = Attribute.from_dict("counter", resp.value)
        self.assertEqual(0, attr.value)

        post = Request.Post(response_queue=q, context="ClientConnection",
                            endpoint=["counting", "increment"])
        process.q.put(post)
        resp = q.get(timeout=1)
        self.assertEqual(Response.RETURN, resp.type_)


        process.stop()
if __name__ == "__main__":
    unittest.main(verbosity=2)
