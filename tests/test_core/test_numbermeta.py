import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

import numpy as np

from malcolm.core.numbermeta import NumberMeta
from malcolm.core.serializable import Serializable


class TestNumberMeta(unittest.TestCase):

    def test_init(self):
        dtype = np.float64
        nm = NumberMeta("nm", "desc", dtype)
        self.assertEqual(nm.typeid, "malcolm:core/NumberMeta:1.0")
        self.assertEqual(nm.dtype, dtype)
        self.assertEqual(nm.label, "nm")

    def test_to_dict(self):
        nm = NumberMeta("nm", "desc", np.float64)
        expected = OrderedDict()
        expected["typeid"] = "malcolm:core/NumberMeta:1.0"
        expected["dtype"] = "float64"
        expected["description"] = "desc"
        expected["tags"] = []
        expected["writeable"] = True
        expected["label"] = "nm"

        self.assertEqual(expected, nm.to_dict())

    def test_from_dict(self):
        d = {"description": "desc", "tags": [], "writeable": True,
             "dtype": "float64", "label": "test_label"}
        nm = NumberMeta.from_dict("nm", d)
        self.assertEqual(NumberMeta, type(nm))
        self.assertEqual("nm", nm.name)
        self.assertEqual(np.float64, nm.dtype)
        self.assertEqual("test_label", nm.label)


class TestNumberMetaValidation(unittest.TestCase):

    def test_float_against_float32(self):
        nm = NumberMeta("nm", "desc", np.float32)
        self.assertAlmostEqual(123.456, nm.validate(123.456), places=5)

    def test_float_against_float64(self):
        nm = NumberMeta("nm", "desc", np.float64)
        self.assertEqual(123.456, nm.validate(123.456))

    def test_int_against_float(self):
        nm = NumberMeta("nm", "desc", np.float64)
        self.assertEqual(123, nm.validate(123))

    def test_int_against_int(self):
        nm = NumberMeta("nm", "desc", np.int32)
        self.assertEqual(123, nm.validate(123))

    def test_float_fails_against_int(self):
        nm = NumberMeta("nm", "desc", np.int32)
        self.assertRaises(ValueError, nm.validate, 123.456)

    def test_none_validates(self):
        nm = NumberMeta("nm", "desc", np.int32)
        self.assertIsNone(nm.validate(None))

if __name__ == "__main__":
    unittest.main(verbosity=2)
