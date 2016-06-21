import unittest

from . import util
from mock import MagicMock, call

# module imports
from malcolm.core.controller import Controller


class DummyController(Controller):
    def say_hello(self, name):
        print("Hello" + name)
    say_hello.Method = MagicMock()

    def say_goodbye(self, name):
        print("Goodbye" + name)
    say_goodbye.Method = MagicMock()


class TestController(unittest.TestCase):

    def test_init(self):
        b = MagicMock()
        c = DummyController(b)
        self.assertEqual(c.block, b)
        b.add_method.assert_has_calls(
            [call(c.say_goodbye.Method), call(c.say_hello.Method)])

if __name__ == "__main__":
    unittest.main(verbosity=2)
