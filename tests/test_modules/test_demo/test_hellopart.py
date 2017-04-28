import unittest
from mock import Mock

from malcolm.modules.demo.parts import HelloPart
from malcolm.core import call_with_params


class TestHelloPart(unittest.TestCase):

    def setUp(self):
        self.c = call_with_params(HelloPart, name='block')

    def test_say_hello(self):
        expected = "Hello test_name"

        parameters_mock = Mock()
        parameters_mock.name = "test_name"
        parameters_mock.sleep = 0
        returns_mock = Mock()
        response = self.c.greet(parameters_mock, returns_mock)
        assert expected == response.greeting
