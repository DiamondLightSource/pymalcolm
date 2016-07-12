import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock

from malcolm.core.notifier import Notifier
from malcolm.core.serializable import Serializable


Serializable.register_subclass("notifier:test")(Notifier)

class TestInit(unittest.TestCase):

    def test_init(self):
        n = Notifier("notifier")
        self.assertEqual("notifier", n.name)
        self.assertEqual("notifier:test", n.typeid)

class TestUpdates(unittest.TestCase):

    def test_parent(self):
        parent = Mock()
        parent.name = "parent"
        n = Notifier("serialize")
        n.set_parent(parent)
        self.assertIs(parent, n.parent)
        self.assertEquals("parent.serialize", n._logger_name)

    def test_on_changed(self):
        change = [["test_attr", "test_value"], 12]
        parent = Mock()
        n = Notifier("test_n")
        n.set_parent(parent)
        notify_flag = Mock()
        n.on_changed(change, notify_flag)
        expected = [["test_n", "test_attr", "test_value"], 12]
        parent.on_changed.assert_called_once_with(expected, notify_flag)

    def test_on_change_notify_flag_default(self):
        parent = Mock()
        n = Notifier("test_n")
        n.set_parent(parent)
        change = [[], Mock()]
        n.on_changed(change)
        parent.on_changed.assert_called_once_with(change, True)

    def test_nop_with_no_parent(self):
        change = [["test"], 123]
        n = Notifier("test_n")
        self.assertIsNone(n.parent)
        n.on_changed(change)
        self.assertEquals([["test"], 123], change)

    def test_endpoint(self):
        n = Notifier("test_n")
        parent = Mock()
        endpoint = Mock()
        notify = Mock()
        n.set_parent(parent)
        n.set_endpoint("end", endpoint, notify)
        parent.on_changed.assert_called_once_with(
            [["test_n", "end"], endpoint], notify)

if __name__ == "__main__":
    unittest.main(verbosity=2)
