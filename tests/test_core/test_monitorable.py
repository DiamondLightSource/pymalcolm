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
        n.set_process_path(p, ["notifier"])
        self.assertEqual(["notifier"], n.process_path)


class TestUpdates(unittest.TestCase):

    def test_set_parent(self):
        class MyMonitorable(Monitorable):
            endpoints = ["child"]

        parent = Mock()
        n = MyMonitorable()
        n.set_endpoint_data("child", Mock())
        n.set_process_path(parent, ["serialize"])
        self.assertIs(parent, n.process)
        self.assertEquals("serialize", n._logger.name)
        n.child.set_process_path.assert_called_once_with(
            parent, ["serialize", "child"])

    def test_apply_changes(self):
        class MyMonitorable(Monitorable):
            endpoints = ["test_value"]
            def set_test_value(self, value, notify=False):
                self.set_endpoint_data("test_value", value, notify)

        change = [["test_value"], 12]
        n = MyMonitorable()
        n.set_endpoint_data("test_value", 10)
        n.set_test_value = Mock(wraps=n.set_test_value)
        process = Mock()
        n.set_process_path(process, ["test_n", "test_attr"])
        n.apply_changes(change)
        expected = [["test_n", "test_attr", "test_value"], 12]
        n.set_test_value.assert_called_once_with(12, notify=False)
        process.report_changes.assert_called_once_with(expected)

    def test_set_endpoint(self):
        n = Monitorable()
        parent = Mock()
        endpoint = Mock()
        # Check that the mock looks like it is serializable
        self.assertTrue(hasattr(endpoint, "to_dict"))
        n.set_process_path(parent, ["test_n"])
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
        n.set_process_path(parent, ("test_n",))
        n.endpoints = ["end"]
        n.set_endpoint_data("end", endpoint, notify=False)
        self.assertEqual(n.end, endpoint)
        self.assertEqual(parent.report_changes.called, False)

if __name__ == "__main__":
    unittest.main(verbosity=2)
