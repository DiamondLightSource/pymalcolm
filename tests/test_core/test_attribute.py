import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock

from malcolm.core.attribute import Attribute
from malcolm.core.ntscalar import NTScalar
from malcolm.modules.builtin.vmetas import StringMeta


class TestAttribute(unittest.TestCase):
    def setUp(self):
        self.data = NTScalar(StringMeta())
        self.data.set_notifier_path(Mock(), ["block", "attr"])
        self.controller = Mock()
        self.context = Mock()
        self.o = Attribute(self.controller, self.context, self.data)

    def test_init(self):
        self.assertIsInstance(self.o, Attribute)
        self.assertTrue(hasattr(self.o, "meta"))
        self.assertTrue(hasattr(self.o, "subscribe_meta"))
        self.assertTrue(hasattr(self.o, "value"))
        self.assertTrue(hasattr(self.o, "subscribe_value"))

    def test_put(self):
        self.o.put_value(32)
        self.context.put.assert_called_once_with(["block", "attr", "value"], 32)

    def test_put_async(self):
        f = self.o.put_value_async(32)
        self.context.put_async.assert_called_once_with(
            ["block", "attr", "value"], 32)
        self.assertEqual(f, self.context.put_async.return_value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
