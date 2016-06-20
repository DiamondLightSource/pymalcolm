import unittest

from . import util
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
        changes = [ (["test_attr", "test_value"], 12),
                    (["test_thing"], 231) ]
        parent = Mock()
        m = Monitorable("test_m")
        m.set_parent(parent)
        m.on_changed(changes)
        expected = [ (["test_m", "test_attr", "test_value"], 12),
                     (["test_m", "test_thing"], 231) ]
        parent.on_changed.assert_called_once_with(expected)

    def test_nop_with_no_parent(self):
        changes = [ (["test"], 123) ]
        m = Monitorable("test_m")
        self.assertIsNone(m.parent)
        m.on_changed(changes)
        self.assertEquals([(["test"], 123)], changes)

if __name__ == "__main__":
    unittest.main(verbosity=2)
