import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import Mock, patch

from malcolm.core.attribute import Attribute
from malcolm.core.attributemeta import AttributeMeta


class TestAttribute(unittest.TestCase):

    def setUp(self):
        self.meta = Mock()
        self.meta.name = "test"
        self.meta.attribute_type.return_value = AttributeMeta.TABLE

    def test_init(self):
        a = Attribute(self.meta)
        self.assertEquals("test", a.name)
        self.assertIs(self.meta, a.meta)
        self.assertIsNone(a.value)
        self.assertEquals("malcolm:core/TableAttribute:1.0", a.typeid)

    def test_set_put_function(self):
        func = Mock()
        a = Attribute(self.meta)
        a.set_put_function(func)
        self.assertIs(func, a.put_func)

    def test_set_value(self):
        value = "test_value"
        a = Attribute(self.meta)
        a.on_changed = Mock(a.on_changed)
        a.set_value(value)
        self.assertEquals("test_value", a.value)
        a.on_changed.assert_called_once_with([['value'], value])

    def test_put(self):
        func = Mock()
        value = "test_value"
        a = Attribute(self.meta)
        a.set_put_function(func)
        a.put(value)
        func.assert_called_once_with(value)

    def test_to_dict(self):
        self.meta.to_dict = Mock(return_value = {"test_meta":"dict"})
        expected = OrderedDict()
        expected["value"] = "test_value"
        expected["meta"] = {"test_meta":"dict"}
        expected["typeid"] = "malcolm:core/TableAttribute:1.0"
        a = Attribute(self.meta)
        a.set_value("test_value")
        self.assertEquals(expected, a.to_dict())

    @patch.object(AttributeMeta, "from_dict")
    def test_from_dict(self, am_from_dict):
        am_from_dict.return_value = self.meta
        d = {"value":"test_value", "meta":{"meta":"dict"}}
        a = Attribute.from_dict("test", d)
        self.assertEquals("test", a.name)
        self.assertEquals("test_value", a.value)
        self.assertIs(self.meta, a.meta)

    def test_meta_types(self):
        meta = Mock()
        meta.name = "test"

        meta.attribute_type.return_value = AttributeMeta.SCALAR
        a = Attribute(meta)
        self.assertEqual("epics:nt/NTScalar:1.0", a.typeid)

        meta.attribute_type.return_value = AttributeMeta.SCALARARRAY
        a = Attribute(meta)
        self.assertEqual("epics:nt/NTScalarArray:1.0", a.typeid)

        meta.attribute_type.return_value = AttributeMeta.TABLE
        a = Attribute(meta)
        self.assertEqual(
            "malcolm:core/TableAttribute:1.0", a.typeid)

    def test_invalid_meta_type_raises(self):
        meta = Mock()
        meta.name = "test"
        meta.attribute_type.return_value = "NOT_A_REAL_TYPE"
        with self.assertRaises(ValueError):
            a = Attribute(meta)

if __name__ == "__main__":
    unittest.main(verbosity=2)
