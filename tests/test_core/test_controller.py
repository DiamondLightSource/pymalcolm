import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# mock
from pkg_resources import require
require("mock")
from mock import MagicMock, call

# module imports
from malcolm.core.controller import Controller


class DummyController(Controller):
    def __init__(self, mock_methods, block):
        self.mock_methods = mock_methods
        super(DummyController, self).__init__(block)

    def create_methods(self):
        return self.mock_methods


class TestController(unittest.TestCase):

    def test_init(self):
        m1 = MagicMock()
        m2 = MagicMock()
        b = MagicMock()
        c = DummyController([m1, m2], b)
        self.assertEqual(c.block, b)
        b.add_method.assert_has_calls([call(m1), call(m2)])

if __name__ == "__main__":
    unittest.main(verbosity=2)
