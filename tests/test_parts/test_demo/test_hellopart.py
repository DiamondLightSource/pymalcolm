import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock

from malcolm.parts.demo.hellopart import HelloPart


class TestHelloPart(unittest.TestCase):

    def setUp(self):
        self.c = HelloPart('block', MagicMock())

    def test_say_hello(self):
        expected = "Hello test_name"

        parameters_mock = Mock()
        parameters_mock.name = "test_name"
        parameters_mock.sleep = 0
        returns_mock = Mock()
        response = self.c.say_hello(parameters_mock, returns_mock)
        self.assertEquals(expected, response.greeting)

if __name__ == "__main__":
    unittest.main(verbosity=2)
