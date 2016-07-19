import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock

# module imports
from malcolm.gui.parameteritem import ParameterItem


class TestParameterItem(unittest.TestCase):

    def setUp(self):
        ref = MagicMock()
        ParameterItem.items.clear()
        self.item = ParameterItem(("endpoint",), ref, 42)

    def test_init(self):
        self.assertEqual(self.item.default, 42)
        self.assertEqual(self.item.get_value(), 42)
        self.assertEqual(self.item.get_state(), self.item.IDLE)

    def test_set_reset(self):
        self.item.ref.validate.side_effect = int
        ret = self.item.set_value(32)
        self.assertEqual(ret, None)
        self.assertEqual(self.item.get_state(), self.item.CHANGED)
        self.assertEqual(self.item.get_value(), 32)
        self.item.reset_value()
        self.assertEqual(self.item.get_state(), self.item.IDLE)
        self.assertEqual(self.item.get_value(), 42)

    def test_bad_value(self):
        self.item.ref.validate.side_effect = int
        self.item.set_value("hello")
        self.assertEqual(self.item.get_state(), self.item.ERROR)
        self.assertEqual(self.item.get_value(), 42)

    def test_get_writeable(self):
        self.assertEqual(self.item.get_writeable(), self.item.ref.writeable)


if __name__ == "__main__":
    unittest.main(verbosity=2)

