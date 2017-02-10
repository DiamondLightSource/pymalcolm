import os
import sys
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths
import unittest

from malcolm.core.vmetas import ChoiceArrayMeta


class TestInit(unittest.TestCase):
    def test_init(self):
        self.meta = ChoiceArrayMeta("test description", ["a", "b"])
        self.assertEqual("test description", self.meta.description)
        self.assertEqual(self.meta.label, "")
        self.assertEqual(self.meta.typeid, "malcolm:core/ChoiceArrayMeta:1.0")
        self.assertEqual(self.meta.choices, ("a", "b"))


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.meta = ChoiceArrayMeta("test description", ["a", "b"])

    def test_validate_none(self):
        self.assertEquals(self.meta.validate(None), ())

    def test_validate(self):
        response = self.meta.validate(["b", "a"])
        self.assertEqual(("b", "a"), response)

    def test_not_iterable_raises(self):
        value = "abb"
        self.assertRaises(ValueError, self.meta.validate, value)

    def test_null_element_raises(self):
        array = ["b", None]
        self.assertRaises(ValueError, self.meta.validate, array)

    def test_invalid_choice_raises(self):
        with self.assertRaises(ValueError):
            self.meta.validate(["a", "x"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
