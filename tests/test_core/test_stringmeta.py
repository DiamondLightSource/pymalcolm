import unittest
from collections import OrderedDict

from malcolm.core.stringmeta import StringMeta
from malcolm.core.attributemeta import AttributeMeta

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestInit(unittest.TestCase):

    def setUp(self):
        self.string_meta = StringMeta("TestMeta")

    def test_given_name_then_set(self):
        self.assertEqual("TestMeta", self.string_meta.name)

    def test_metaOf(self):
        self.assertEqual(StringMeta.metaOf, "malcolm:core/String:1.0")


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.string_meta = StringMeta("TestMeta")

    def test_given_value_str_then_return(self):
        response = self.string_meta.validate("TestValue")

        self.assertEqual("TestValue", response)

    def test_given_value_int_then_cast_and_return(self):
        response = self.string_meta.validate(15)

        self.assertEqual("15", response)

    def test_given_value_float_then_cast_and_return(self):
        response = self.string_meta.validate(12.8)

        self.assertEqual("12.8", response)

    def test_given_value_None_then_return(self):
        response = self.string_meta.validate(None)

        self.assertEqual(None, response)


class TestToDict(unittest.TestCase):

    def setUp(self):
        self.string_meta = StringMeta("Test")

    def test_returns_dict(self):
        expected_dict = OrderedDict()
        expected_dict["metaOf"] = "malcolm:core/String:1.0"

        response = self.string_meta.to_dict()

        self.assertEqual(expected_dict, response)

    def test_from_dict_deserialize(self):
        s = AttributeMeta.from_dict(
            "me", dict(metaOf="malcolm:core/String:1.0"))
        self.assertEqual(type(s), StringMeta)
        self.assertEqual(s.name, "me")

if __name__ == "__main__":
    unittest.main(verbosity=2)
