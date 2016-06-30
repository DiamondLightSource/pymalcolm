import sys
import os
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.booleanmeta import BooleanMeta
from malcolm.core.serializable import Serializable


class TestInit(unittest.TestCase):

    def setUp(self):
        self.boolean_meta = BooleanMeta("TestMeta", "test description")

    def test_values_after_init(self):
        self.assertEqual("TestMeta", self.boolean_meta.name)
        self.assertEqual("test description",
                         self.boolean_meta.description)
        self.assertEqual(self.boolean_meta.typeid, "malcolm:core/Boolean:1.0")

class TestValidate(unittest.TestCase):

    def setUp(self):
        self.boolean_meta = BooleanMeta("TestMeta", "test description")

    def test_given_value_str_then_cast_and_return(self):
        response = self.boolean_meta.validate("TestValue")
        self.assertTrue(response)

        response = self.boolean_meta.validate("")
        self.assertFalse(response)

    def test_given_value_int_then_cast_and_return(self):
        response = self.boolean_meta.validate(15)
        self.assertTrue(response)

        response = self.boolean_meta.validate(0)
        self.assertFalse(response)

    def test_given_value_boolean_then_cast_and_return(self):
        response = self.boolean_meta.validate(True)
        self.assertTrue(response)

        response = self.boolean_meta.validate(False)
        self.assertFalse(response)

    def test_given_value_None_then_return(self):
        response = self.boolean_meta.validate(None)

        self.assertEqual(None, response)


class TestSerialisation(unittest.TestCase):

    def setUp(self):
        self.string_meta = BooleanMeta("Test", "test description")

    def test_to_dict(self):
        expected_dict = OrderedDict()
        expected_dict["description"] = "test description"
        expected_dict["typeid"] = "malcolm:core/Boolean:1.0"

        response = self.string_meta.to_dict()

        self.assertEqual(expected_dict, response)

    def test_from_dict(self):
        d = dict(description="test description",
                 typeid="malcolm:core/Boolean:1.0")
        s = Serializable.from_dict("me", d)
        self.assertEqual(type(s), BooleanMeta)
        self.assertEqual(s.name, "me")

if __name__ == "__main__":
    unittest.main(verbosity=2)
