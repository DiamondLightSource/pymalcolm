import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.vmetas import NumberMeta
from malcolm.core.serializable import Serializable


class TestInit(unittest.TestCase):
    def test_init(self):
        nm = NumberMeta("float32")
        self.assertEqual(nm.typeid, "malcolm:core/NumberMeta:1.0")
        self.assertEqual(nm.dtype, "float32")
        self.assertEqual(nm.label, "")


class TestValidate(unittest.TestCase):

    def test_float_against_float32(self):
        nm = NumberMeta("float32")
        self.assertAlmostEqual(123.456, nm.validate(123.456), places=5)

    def test_float_against_float64(self):
        nm = NumberMeta("float64")
        self.assertEqual(123.456, nm.validate(123.456))

    def test_int_against_float(self):
        nm = NumberMeta("float64")
        self.assertEqual(123, nm.validate(123))

    def test_int_against_int(self):
        nm = NumberMeta("int32")
        self.assertEqual(123, nm.validate(123))

    def test_float_fails_against_int(self):
        nm = NumberMeta("int32")
        self.assertRaises(ValueError, nm.validate, 123.456)

    def test_none_validates(self):
        nm = NumberMeta("int32")
        self.assertIsNone(nm.validate(None))


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/NumberMeta:1.0"
        self.serialized["dtype"] = "float64"
        self.serialized["description"] = "desc"
        self.serialized["tags"] = []
        self.serialized["writeable"] = False
        self.serialized["label"] = "name"

    def test_to_dict(self):
        nm = NumberMeta("float64", "desc", label="name")
        self.assertEqual(nm.to_dict(), self.serialized)

    def test_from_dict(self):
        nm = NumberMeta.from_dict(self.serialized)
        self.assertEqual(type(nm), NumberMeta)
        self.assertEquals(nm.description, "desc")
        self.assertEquals(nm.dtype, "float64")
        self.assertEqual(nm.tags, [])
        self.assertFalse(nm.writeable)
        self.assertEqual(nm.label, "name")


if __name__ == "__main__":
    unittest.main(verbosity=2)
