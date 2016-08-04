import sys
import os
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.vmetas import BooleanMeta


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.boolean_meta = BooleanMeta("test description")

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

if __name__ == "__main__":
    unittest.main(verbosity=2)
