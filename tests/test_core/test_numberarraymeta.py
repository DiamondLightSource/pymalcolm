import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

import numpy as np

from malcolm.core.numberarraymeta import NumberArrayMeta


class TestNumberMeta(unittest.TestCase):

    def setUp(self):
        self.dtype = np.float64
        self.nm = NumberArrayMeta("nm", "desc", self.dtype)

    def test_init(self):
        self.assertEqual(self.nm.typeid, "malcolm:core/NumberArrayMeta:1.0")
        self.assertEqual(self.nm.dtype, self.dtype)
        self.assertEqual(self.nm.label, "nm")

    def test_to_dict(self):
        expected = OrderedDict()
        expected["typeid"] = "malcolm:core/NumberArrayMeta:1.0"
        expected["dtype"] = "float64"
        expected["description"] = "desc"
        expected["tags"] = []
        expected["writeable"] = True
        expected["label"] = "nm"

        self.assertEqual(expected, self.nm.to_dict())

    def test_from_dict(self):
        d = {"description": "desc", "tags": [], "writeable": True,
             "typeid": "malcolm:core/NumberMeta:1.0",
             "dtype": "float64", "label": "test_label"}
        nm = self.nm.from_dict("nm", d)
        self.assertEqual(NumberArrayMeta, type(nm))
        self.assertEqual("nm", nm.name)
        self.assertEqual(np.float64, nm.dtype)
        self.assertEqual("test_label", nm.label)


class TestNumberMetaValidation(unittest.TestCase):

    def test_float_against_float64(self):
        nm = NumberArrayMeta("nm", "desc", np.float64)
        values = [1.2, 3.4, 5.6]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertEqual(values[i], value)

    def test_float_against_float32(self):
        nm = NumberArrayMeta("nm", "desc", np.float32)
        values = [1.2, 3.4, 5.6]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertAlmostEqual(values[i], response[i], places=5)

    def test_int_against_float(self):
        nm = NumberArrayMeta("nm", "desc", np.float32)
        values = [1, 2, 3]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertEqual(values[i], value)

        nm = NumberArrayMeta("nm", "desc", np.float64)
        values = [1, 2, 3]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertEqual(values[i], value)

    def test_int_against_int(self):
        nm = NumberArrayMeta("nm", "desc", np.int32)
        values = [1, 2, 3]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertEqual(values[i], value)

    def test_float_against_int_raises(self):
        nm = NumberArrayMeta("nm", "desc", np.int32)
        self.assertRaises(ValueError, nm.validate, [1.2, 34, 56])

    def test_null_element_raises(self):
        nm = NumberArrayMeta("nm", "desc", np.float32)
        self.assertRaises(ValueError, nm.validate, [1.2, None, 5.6])

    def test_none_validates(self):
        nm = NumberArrayMeta("nm", "desc", np.int32)
        self.assertIsNone(nm.validate(None))

if __name__ == "__main__":
    unittest.main(verbosity=2)
