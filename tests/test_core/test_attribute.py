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
        assert hasattr(self.o, "meta")
        assert hasattr(self.o, "subscribe_meta")
        assert hasattr(self.o, "value")
        assert hasattr(self.o, "subscribe_value")

    def test_put(self):
        self.o.put_value(32)
        self.context.put.assert_called_once_with(["block", "attr", "value"], 32)

    def test_put_async(self):
        f = self.o.put_value_async(32)
        self.context.put_async.assert_called_once_with(
            ["block", "attr", "value"], 32)
        assert f == self.context.put_async.return_value
