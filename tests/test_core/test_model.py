import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock

from malcolm.core.model import Model


class MyModel(Model):
    endpoints = ["child"]
    child = None


class TestModel(unittest.TestCase):

    def setUp(self):
        self.notifier = MagicMock()
        self.child = Mock()
        self.o = MyModel()

    def test_set_endpoint_no_notifier(self):
        c = self.o.set_endpoint_data("child", self.child)
        self.assertEqual(c, self.child)

    def test_set_notifier_child(self):
        self.o.set_endpoint_data("child", self.child)
        self.o.set_notifier_path(self.notifier, ["serialize"])

    def test_set_endpoint(self):
        self.o.set_notifier_path(self.notifier, ["thing"])
        self.o.set_endpoint_data("child", self.child)
        self.notifier.add_squashed_change.assert_called_once_with(
            ["thing", "child"], self.child)

if __name__ == "__main__":
    unittest.main(verbosity=2)
