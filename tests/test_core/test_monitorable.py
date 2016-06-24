import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock

from malcolm.core.monitorable import Monitorable


class TestMonitorable(unittest.TestCase):

    def test_init(self):
        m = Monitorable("mon")
        self.assertEqual("mon", m.name)

    def test_parent(self):
        parent = Mock()
        parent.name = "parent"
        m = Monitorable("mon")
        m.set_parent(parent)
        self.assertIs(parent, m.parent)
        self.assertEquals("parent.mon", m._logger_name)

    def test_on_changed(self):
        change = [["test_attr", "test_value"], 12]
        parent = Mock()
        m = Monitorable("test_m")
        m.set_parent(parent)
        m.on_changed(change)
        expected = [["test_m", "test_attr", "test_value"], 12]
        parent.on_changed.assert_called_once_with(expected)

    def test_nop_with_no_parent(self):
        change = [["test"], 123]
        m = Monitorable("test_m")
        self.assertIsNone(m.parent)
        m.on_changed(change)
        self.assertEquals([["test"], 123], change)

if __name__ == "__main__":
    unittest.main(verbosity=2)
