import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# module imports
from malcolm.core.controller import Controller
from malcolm.core.method import Method
from malcolm.core.mapmeta import MapMeta
from malcolm.core.stringmeta import StringMeta
from malcolm.core.block import Block


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
    def setUp(self):
        self.block = Block("Hello")
        self.controller = HelloController(self.block)

    def test_hello_controller_good_input(self):
        result = self.block.say_hello(name = "me")
        self.assertEquals(result["greeting"], "Hello me")

if __name__ == "__main__":
    unittest.main(verbosity=2)
