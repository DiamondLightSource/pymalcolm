import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

import numpy as np

from malcolm.core.numberarraymeta import NumberArrayMeta
from malcolm.core.serializable import Serializable


class TestNumberMeta(unittest.TestCase):

    def setUp(self):
        self.dtype_list = [np.float64, np.float64, np.float64]
        self.nm = NumberArrayMeta("nm", "desc", self.dtype_list)

    def test_init(self):
        self.assertEqual(self.nm.typeid, "malcolm:core/NumberArrayMeta:1.0")
        self.assertEqual(self.nm.dtype_list, self.dtype_list)
        self.assertEqual(self.nm.label, "nm")

    def test_to_dict(self):
        expected = OrderedDict()
        expected["typeid"] = "malcolm:core/NumberArrayMeta:1.0"
        expected["dtype_list"] = ["float64", "float64", "float64"]
        expected["description"] = "desc"
        expected["tags"] = []
        expected["writeable"] = True
        expected["label"] = "nm"

        self.assertEqual(expected, self.nm.to_dict())

    def test_from_dict(self):
        d = {"description": "desc", "tags": [], "writeable": True,
             "typeid": "malcolm:core/NumberMeta:1.0",
             "dtype_list": ["float64", "float64", "float64"], "label": "test_label"}
        nm = self.nm.from_dict("nm", d)
        self.assertEqual(NumberArrayMeta, type(nm))
        self.assertEqual("nm", nm.name)
        self.assertEqual([np.float64, np.float64, np.float64], nm.dtype_list)
        self.assertEqual("test_label", nm.label)


class TestNumberMetaValidation(unittest.TestCase):

    def test_valid_int_float_casts(self):
        nm = NumberArrayMeta("nm", "desc", [np.float64, np.float64, np.int32])
        self.assertEqual([1.2, 34, 56], nm.validate([1.2, 34, 56]))

    def test_float_fails_against_int(self):
        nm = NumberArrayMeta("nm", "desc", [np.int32, np.int32, np.int32])
        self.assertRaises(AssertionError, nm.validate, [1.2, 34, 56])

    def test_none_validates(self):
        nm = NumberArrayMeta("nm", "desc", np.int32)
        self.assertIsNone(nm.validate(None))

if __name__ == "__main__":
    unittest.main(verbosity=2)
