#!/bin/env dls-python

import unittest
from malcolm.core.stringmeta import StringMeta
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestInit(unittest.TestCase):

    def setUp(self):
        self.string_meta = StringMeta("TestMeta", "TestValue")

    def test_given_name_then_set(self):
        self.assertEqual("TestMeta", self.string_meta.name)


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.string_meta = StringMeta("TestMeta", "TestValue")

    def test_given_value_str_then_return(self):
        response = self.string_meta.validate("TestValue")

        self.assertEqual("TestValue", response)

    def test_given_value_int_then_cast_and_return(self):
        response = self.string_meta.validate(15)

        self.assertEqual("15", response)

    def test_given_value_float_then_cast_and_return(self):
        response = self.string_meta.validate(12.8)

        self.assertEqual("12.8", response)

    def test_given_value_dict_then_raise_error(self):
        expected_error_message = "Value must be of type str or castable to str"

        with self.assertRaises(TypeError) as error:
            self.string_meta.validate(dict(x=10))

        self.assertEqual(expected_error_message, error.exception.message)

if __name__ == "__main__":
    unittest.main(verbosity=2)
