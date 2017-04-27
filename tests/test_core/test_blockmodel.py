import unittest

from malcolm.core.blockmodel import BlockModel
from malcolm.core.methodmodel import MethodModel
from malcolm.modules.builtin.vmetas import StringMeta


class TestBlockModel(unittest.TestCase):

    def setUp(self):
        self.attr = StringMeta().create_attribute()
        self.method = MethodModel()
        self.o = BlockModel()
        self.o.set_endpoint_data("attr", self.attr)
        self.o.set_endpoint_data("method", self.method)

    def test_init(self):
        self.assertEqual(self.o.method, self.method)
        self.assertEqual(self.o.attr, self.attr)
        self.assertEqual(self.o.typeid, "malcolm:core/Block:1.0")
        self.assertEqual(self.o.endpoints, ["meta", "attr", "method"])

    def test_remove_endpoint(self):
        self.o.remove_endpoint("attr")
        self.assertEqual(self.o.method, self.method)
        self.assertEqual(self.o.endpoints, ["meta", "method"])
        self.assertEqual(self.o.meta.fields, ("method",))
        with self.assertRaises(AttributeError):
            a = self.o.attr
        self.o.set_endpoint_data("attr", self.attr)
        self.assertEqual(self.o.endpoints, ["meta", "method", "attr"])
        self.assertEqual(self.o.meta.fields, ("method", "attr"))
        self.assertEqual(self.o.attr, self.attr)
