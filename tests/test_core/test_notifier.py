import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock
from collections import OrderedDict

from malcolm.core.notifier import Notifier, NO_VALIDATE


class TestInit(unittest.TestCase):

    def test_init(self):
        p = Mock()
        n = Notifier()
        self.assertFalse(hasattr(n, 'parent'))
        n.set_parent(p, "notifier")
        self.assertEqual("notifier", n.name)


class TestUpdates(unittest.TestCase):

    def test_set_parent(self):
        class MyNotifier(Notifier):
            endpoints = ["child"]
            child = Mock()
        parent = Mock()
        parent.name = "parent"
        n = MyNotifier()
        n.set_parent(parent, "serialize")
        self.assertIs(parent, n.parent)
        self.assertEquals("serialize", n._logger.name)
        n.child.set_logger_name.assert_called_once_with("serialize.child")

    def test_on_changed(self):
        change = [["test_attr", "test_value"], 12]
        parent = Mock()
        n = Notifier()
        n.set_parent(parent,"test_n")
        notify = Mock()
        n.on_changed(change, notify)
        expected = [["test_n", "test_attr", "test_value"], 12]
        parent.on_changed.assert_called_once_with(expected, notify)

    def test_on_change_notify_flag_default(self):
        parent = Mock()
        n = Notifier()
        n.set_parent(parent,"test_n")
        change = [[], Mock()]
        n.on_changed(change)
        parent.on_changed.assert_called_once_with(change, True)

    def test_nop_with_no_parent(self):
        change = [["test"], 123]
        n = Notifier()
        with self.assertRaises(AttributeError):
            p = n.parent
        n.on_changed(change)
        self.assertEquals([["test"], 123], change)

    def test_set_endpoint(self):
        n = Notifier()
        parent = Mock()
        endpoint = Mock()
        # Check that the mock looks like it is serializable
        self.assertTrue(hasattr(endpoint, "to_dict"))
        notify = Mock()
        n.set_parent(parent,"test_n")
        n.set_endpoint(NO_VALIDATE, "end", endpoint, notify)
        self.assertEqual(n.end, endpoint)
        parent.on_changed.assert_called_once_with(
            [["test_n", "end"], endpoint.to_dict()], notify)



if __name__ == "__main__":
    unittest.main(verbosity=2)
