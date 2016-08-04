import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest

from malcolm.core.vmetas import StringMeta
from malcolm.core.serializable import Serializable


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.string_meta = StringMeta("test string description")

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
