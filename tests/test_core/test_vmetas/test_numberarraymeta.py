import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

import numpy as np

from malcolm.core.vmetas import NumberArrayMeta


class TestValidation(unittest.TestCase):

    def test_numpy_array(self):
        nm = NumberArrayMeta("float64")
        values = np.array([1.2, 3.4, 5.6])
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertEqual(values[i], value)

    def test_numpy_array_wrong_type_raises(self):
        nm = NumberArrayMeta("float64")
        values = "[1.2, 3.4, 5.6]"

        with self.assertRaises(TypeError):
            nm.validate(values)

    def test_numpy_array_wrong_number_type_raises(self):
        nm = NumberArrayMeta("int32")
        values = np.array([1.2, 3.4, 5.6])

        with self.assertRaises(TypeError):
            nm.validate(values)

    def test_float_against_float64(self):
        nm = NumberArrayMeta("float64")
        values = [1.2, 3.4, 5.6]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertEqual(values[i], value)

    def test_float_against_float32(self):
        nm = NumberArrayMeta("float32")
        values = [1.2, 3.4, 5.6]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertAlmostEqual(values[i], response[i], places=5)

    def test_int_against_float(self):
        nm = NumberArrayMeta("float32")
        values = [1, 2, 3]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertEqual(values[i], value)

        nm = NumberArrayMeta("float64")
        values = [1, 2, 3]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertEqual(values[i], value)

    def test_int_against_int(self):
        nm = NumberArrayMeta("int32")
        values = [1, 2, 3]
        response = nm.validate(values)

        for i, value in enumerate(response):
            self.assertEqual(values[i], value)

    def test_float_against_int_raises(self):
        nm = NumberArrayMeta("int32")
        self.assertRaises(ValueError, nm.validate, [1.2, 34, 56])

    def test_null_element_raises(self):
        nm = NumberArrayMeta("float32")
        self.assertRaises(ValueError, nm.validate, [1.2, None, 5.6])

    def test_none_validates(self):
        nm = NumberArrayMeta("int32")
        self.assertIsNone(nm.validate(None))

if __name__ == "__main__":
    unittest.main(verbosity=2)
