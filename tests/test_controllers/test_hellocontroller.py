import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock

from malcolm.controllers.hellocontroller import HelloController


class TestHelloController(unittest.TestCase):

    def setUp(self):
        self.block = Mock()
        self.c = HelloController(MagicMock(), self.block)

    def test_init(self):
        self.assertIs(self.block, self.c.block)
        self.assertEquals(self.c.say_hello.Method, self.block.add_method.call_args[0][0])

    def test_say_hello(self):
        expected = "Hello test_name"

        parameters_mock = Mock()
        parameters_mock.name = "test_name"
        returns_mock = Mock()
        response = self.c.say_hello(parameters_mock, returns_mock)
        self.assertEquals(expected, response.greeting)

if __name__ == "__main__":
    unittest.main(verbosity=2)
