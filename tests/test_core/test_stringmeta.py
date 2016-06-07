import sys
import os
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from malcolm.core.stringmeta import StringMeta
from malcolm.core.attributemeta import AttributeMeta


class TestInit(unittest.TestCase):

    def setUp(self):
        self.string_meta = StringMeta("TestMeta", "test string description")

    def test_values_after_init(self):
        self.assertEqual("TestMeta", self.string_meta.name)
        self.assertEqual("test string description",
                         self.string_meta.description)

    def test_metaOf(self):
        self.assertEqual(StringMeta.metaOf, "malcolm:core/String:1.0")


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.string_meta = StringMeta("TestMeta", "test string description")

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
        self.string_meta = StringMeta("Test", "test string description")

    def test_returns_dict(self):
        expected_dict = OrderedDict()
        expected_dict["description"] = "test string description"
        expected_dict["metaOf"] = "malcolm:core/String:1.0"

        response = self.string_meta.to_dict()

        self.assertEqual(expected_dict, response)

    def test_from_dict_deserialize(self):
        d = dict(description="test string description",
                 metaOf="malcolm:core/String:1.0")
        s = AttributeMeta.from_dict("me", d)
        self.assertEqual(type(s), StringMeta)
        self.assertEqual(s.name, "me")

if __name__ == "__main__":
    unittest.main(verbosity=2)
