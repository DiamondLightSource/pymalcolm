import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock
from collections import OrderedDict

from malcolm.core.monitorable import Monitorable


class TestInit(unittest.TestCase):

    def test_init(self):
        p = Mock()
        n = Monitorable()
        self.assertIsNone(n._parent)
        n.set_parent(p, "notifier")
        self.assertEqual("notifier", n._name)


class TestUpdates(unittest.TestCase):

    def test_set_parent(self):
        class MyMonitorable(Monitorable):
            endpoints = ["child"]

        parent = Mock()
        n = MyMonitorable()
        n.set_endpoint_data("child", Mock())
        n.set_parent(parent, "serialize")
        self.assertIs(parent, n._parent)
        self.assertEquals("serialize", n._logger.name)
        n.child.set_logger_name.assert_called_once_with("serialize.child")

    def test_report_changed(self):
        change = [["test_attr", "test_value"], 12]
        parent = Mock()
        n = Monitorable()
        n.set_parent(parent,"test_n")
        notify = Mock()
        n.report_changes(change)
        expected = [["test_n", "test_attr", "test_value"], 12]
        parent.report_changes.assert_called_once_with(expected)

    def test_nop_with_no_parent(self):
        change = [["test"], 123]
        n = Monitorable()
        self.assertIsNone(n._parent)
        n.report_changes(change)
        self.assertEquals([["test"], 123], change)

    def test_set_endpoint(self):
        n = Monitorable()
        parent = Mock()
        endpoint = Mock()
        # Check that the mock looks like it is serializable
        self.assertTrue(hasattr(endpoint, "to_dict"))
        n.set_parent(parent,"test_n")
        n.endpoints = ["end"]
        n.set_endpoint_data("end", endpoint, notify=True)
        self.assertEqual(n.end, endpoint)
        parent.report_changes.assert_called_once_with(
            [["test_n", "end"], endpoint.to_dict()])


    def test_set_endpoint_no_notify(self):
        n = Monitorable()
        parent = Mock()
        endpoint = Mock()
        # Check that the mock looks like it is serializable
        self.assertTrue(hasattr(endpoint, "to_dict"))
        n.set_parent(parent, "test_n")
        n.endpoints = ["end"]
        n.set_endpoint_data("end", endpoint, notify=False)
        self.assertEqual(n.end, endpoint)
        self.assertEqual(parent.report_changes.called, False)

if __name__ == "__main__":
    unittest.main(verbosity=2)
