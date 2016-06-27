import sys
import os
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.enummeta import EnumMeta
from malcolm.core.attributemeta import AttributeMeta


class TestInit(unittest.TestCase):

    def setUp(self):
        self.enum_meta = EnumMeta("TestMeta", "test description", [1, 2, 3])

    def test_values_after_init(self):
        self.assertEqual("TestMeta", self.enum_meta.name)
        self.assertEqual("test description",
                         self.enum_meta.description)
        self.assertEqual(self.enum_meta.metaOf, "malcolm:core/Enum:1.0")


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.enum_meta = EnumMeta("TestMeta", "test description", [1, 2, 3])

    def test_given_valid_value_then_return(self):
        response = self.enum_meta.validate(1)
        self.assertEqual(1, response)

    def test_given_invalid_value_then_raises(self):
        with self.assertRaises(ValueError):
            self.enum_meta.validate(0)

    def test_set_one_of(self):
        self.enum_meta.set_one_of([4, 5, 6])

        self.assertEqual([4, 5, 6], self.enum_meta.oneOf)


class TestSerialisation(unittest.TestCase):

    def setUp(self):
        self.enum_meta = EnumMeta("Test", "test description", [1, 2, 3])

    def test_to_dict(self):
        expected_dict = OrderedDict()
        expected_dict["description"] = "test description"
        expected_dict["metaOf"] = "malcolm:core/Enum:1.0"
        expected_dict["oneOf"] = [1, 2, 3]

        response = self.enum_meta.to_dict()

        self.assertEqual(expected_dict, response)

    def test_from_dict(self):
        d = dict(description="test description",
                 metaOf="malcolm:core/Enum:1.0",
                 oneOf=[1, 2, 3])
        s = AttributeMeta.from_dict("me", d)
        self.assertEqual(type(s), EnumMeta)
        self.assertEqual(s.name, "me")
        self.assertEqual(s.oneOf, [1, 2, 3])

if __name__ == "__main__":
    unittest.main(verbosity=2)
