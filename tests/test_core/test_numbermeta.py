import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict
import numpy as np

import unittest

from malcolm.core.numbermeta import NumberMeta
from malcolm.core.attributemeta import AttributeMeta


class TestNumberMeta(unittest.TestCase):
    def test_init_int(self):
        nm = NumberMeta("nm", "desc", np.int32)
        self.assertEqual(nm.metaOf, "malcolm:core/Int:1.0")

    def test_init_float(self):
        nm = NumberMeta("nm", "desc", np.float64)
        self.assertEqual(nm.metaOf, "malcolm:core/Double:1.0")

    def test_to_dict(self):
        nm = NumberMeta("nm", "desc", np.float64)
        expected = OrderedDict()
        expected["description"] = "desc"
        expected["metaOf"] = "malcolm:core/Double:1.0"

        self.assertEqual(expected, nm.to_dict())

    def test_from_dict(self):
        d = {"description":"desc", "metaOf":"malcolm:core/Double:1.0"}
        nm = AttributeMeta.from_dict("nm", d)
        self.assertEqual(NumberMeta, type(nm))
        self.assertEqual("nm", nm.name)
        self.assertEqual(np.float64, nm.dtype)

    def test_is_scalar(self):
        nm = NumberMeta("nm", "desc", np.int32)
        self.assertEqual(AttributeMeta.SCALAR, nm.attribute_type())

class TestNumberMetaValidation(unittest.TestCase):
    def test_float_against_float(self):
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
        self.assertRaises(AssertionError, nm.validate, 123.456)

    def test_none_validates(self):
        nm = NumberMeta("nm", "desc", np.int32)
        self.assertIsNone(nm.validate(None))

if __name__ == "__main__":
    unittest.main(verbosity=2)
