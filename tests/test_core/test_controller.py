import unittest

from . import util
from mock import MagicMock, call

# module imports
from malcolm.core.controller import Controller


class DummyController(Controller):
    def __init__(self, mock_methods, block):
        self.mock_methods = mock_methods
        super(DummyController, self).__init__(block)

    def say_hello(self, name):
        print("Hello" + name)
    say_hello.Method = MagicMock()

    def say_goodbye(self, name):
        print("Goodbye" + name)
    say_goodbye.Method = MagicMock()


class TestController(unittest.TestCase):

    def test_init(self):
        m1 = MagicMock()
        m2 = MagicMock()
        b = MagicMock()
        c = DummyController([m1, m2], b)
        self.assertEqual(c.block, b)
        b.add_method.assert_has_calls([call(c.say_goodbye), call(c.say_hello)])

    def test_find_decorated_functions(self):
        m1 = MagicMock()
        m2 = MagicMock()
        b = MagicMock()
        c = DummyController([m1, m2], b)

        methods = []
        for member in c.create_methods():
            methods.append(member)

        self.assertEqual(2, len(methods))
        method_names = [method.__func__.__name__ for method in methods]
        self.assertIn("say_hello", method_names)
        self.assertIn("say_goodbye", method_names)

if __name__ == "__main__":
    unittest.main(verbosity=2)
