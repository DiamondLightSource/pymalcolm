import unittest

from . import util
from mock import Mock

from malcolm.controllers.hellocontroller import HelloController


class TestHelloController(unittest.TestCase):
    def test_init(self):
        block = Mock()
        c = HelloController(block)
        self.assertIs(block, c.block)
        self.assertEquals(c.say_hello, block.add_method.call_args[0][0].func)

    def test_say_hello(self):
        c = HelloController(Mock())
        args = {"name":"test_name"}
        expected = {"greeting":"Hello test_name"}
        self.assertEquals(expected, c.say_hello(args))

if __name__ == "__main__":
    unittest.main(verbosity=2)
