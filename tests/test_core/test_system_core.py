import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core.controller import Controller
from malcolm.core.method import Method
from malcolm.core.mapmeta import MapMeta
from malcolm.core.stringmeta import StringMeta
from malcolm.core.block import Block
from malcolm.core.process import Process
from malcolm.core.syncfactory import SyncFactory
from malcolm.core.request import Request


class HelloController(Controller):
    def say_hello(self, args):
        """Says Hello to name

        Args:
            name (str): The name of the person to say hello to

        Returns:
            str: The greeting
        """
        return dict(greeting="Hello %s" % args["name"])

    def create_methods(self):
        """Create a Method wrapper for say_hello and return it"""
        method = Method("say_hello")
        method.set_function(self.say_hello)
        takes = MapMeta("takes")
        takes.add_element(StringMeta("name"))
        method.set_function_takes(takes)
        returns = MapMeta("returns")
        returns.add_element(StringMeta("greeting"))
        method.set_function_returns(returns)
        yield method


class TestSystemCore(unittest.TestCase):

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

if __name__ == "__main__":
    unittest.main(verbosity=2)
