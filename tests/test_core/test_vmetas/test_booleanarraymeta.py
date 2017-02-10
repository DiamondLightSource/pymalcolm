import os
import sys
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths
import unittest

from malcolm.core.vmetas import BooleanArrayMeta


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.meta = BooleanArrayMeta("test description")

    def test_init(self):
        self.assertEqual("test description", self.meta.description)
        self.assertEqual(self.meta.label, "")
        self.assertEqual(self.meta.typeid, "malcolm:core/BooleanArrayMeta:1.0")

    def test_validate_none(self):
        self.assertEquals(list(self.meta.validate(None)), [])

    def test_validate_array(self):
        array = ["True", "", True, False, 1, 0]
        self.assertEquals(
            [True, False, True, False, True, False],
            list(self.meta.validate(array)))

    def test_not_iterable_raises(self):
        value = True
        self.assertRaises(TypeError, self.meta.validate, value)

    def test_null_element_raises(self):
        array = ["test", None]
        self.assertEquals(
            [True, False], list(self.meta.validate(array)))

if __name__ == "__main__":
    unittest.main(verbosity=2)
