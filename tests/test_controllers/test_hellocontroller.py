import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from pkg_resources import require
require("mock")
from mock import Mock

from malcolm.controllers.hellocontroller import HelloController


class TestHelloController(unittest.TestCase):
    def test_init(self):
        block = Mock()
        c = HelloController(block)
        self.assertIs(block, c.block)
        block.add_method.assert_called_once()
        self.assertEquals(c.say_hello, block.add_method.call_args[0][0].func)

    def test_say_hello(self):
        c = HelloController(Mock())
        args = {"name":"test_name"}
        expected = {"greeting":"Hello test_name"}
        self.assertEquals(expected, c.say_hello(args))

if __name__ == "__main__":
    unittest.main(verbosity=2)
