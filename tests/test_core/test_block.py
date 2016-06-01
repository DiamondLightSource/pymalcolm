import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# mock
from pkg_resources import require
require("mock")
from mock import MagicMock

# module imports
from malcolm.core.block import Block


class TestBlock(unittest.TestCase):

    def test_init(self):
        b = Block("blockname")
        self.assertEqual(b.name, "blockname")
        self.assertEqual(b._methods.keys(), [])

    def test_add_method_registers(self):
        b = Block("blockname")
        m = MagicMock()
        m.name = "mymethod"
        b.add_method(m)
        self.assertEqual(b._methods.keys(), ["mymethod"])
        self.assertFalse(m.called)
        m.return_value = 42
        self.assertEqual(b.mymethod(), 42)
        m.assert_called_once_with()

if __name__ == "__main__":
    unittest.main(verbosity=2)
