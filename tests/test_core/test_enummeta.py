import sys
import os
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from malcolm.core.enummeta import EnumMeta
from malcolm.core.attributemeta import AttributeMeta


class TestInit(unittest.TestCase):

    def setUp(self):
        self.boolean_meta = EnumMeta("TestMeta", "test description", [1, 2, 3])

    def test_values_after_init(self):
        self.assertEqual("TestMeta", self.boolean_meta.name)
        self.assertEqual("test description",
                         self.boolean_meta.description)
        self.assertEqual(EnumMeta.metaOf, "malcolm:core/Enum:1.0")


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.boolean_meta = EnumMeta("TestMeta", "test description", [1, 2, 3])

    def test_given_valid_value_then_return(self):
        response = self.boolean_meta.validate(1)
        self.assertEqual(1, response)

    def test_given_invalid_value_then_raises(self):
        with self.assertRaises(ValueError):
            self.boolean_meta.validate(0)


class TestSerialisation(unittest.TestCase):

    def setUp(self):
        self.string_meta = EnumMeta("Test", "test description", [1, 2, 3])

    def test_to_dict(self):
        expected_dict = OrderedDict()
        expected_dict["description"] = "test description"
        expected_dict["metaOf"] = "malcolm:core/Enum:1.0"
        expected_dict["one_of"] = [1, 2, 3]

        response = self.string_meta.to_dict()

        self.assertEqual(expected_dict, response)

    def test_from_dict(self):
        d = dict(description="test description",
                 metaOf="malcolm:core/Enum:1.0",
                 one_of=[1, 2, 3])
        s = AttributeMeta.from_dict("me", d)
        self.assertEqual(type(s), EnumMeta)
        self.assertEqual(s.name, "me")
        self.assertEqual(s.one_of, [1, 2, 3])

if __name__ == "__main__":
    unittest.main(verbosity=2)
