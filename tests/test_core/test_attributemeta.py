#!/bin/env dls-python

import unittest
from collections import OrderedDict

from malcolm.core.attributemeta import AttributeMeta

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestInit(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = AttributeMeta("Test")

    def test_given_name_then_set(self):
        self.assertEqual("Test", self.attribute_meta.name)


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = AttributeMeta("Test")

    def test_given_validate_called_then_raise_error(self):

        expected_error_message = \
            "Abstract validate function must be implemented in child classes"

        with self.assertRaises(NotImplementedError) as error:
            self.attribute_meta.validate(1)

        self.assertEqual(expected_error_message, error.exception.message)


class TestToDict(unittest.TestCase):

    def setUp(self):
        self.attribute_meta = AttributeMeta("Test")

    def test_returns_dict(self):
        expected_dict = OrderedDict()

        response = self.attribute_meta.to_dict()

        self.assertEqual(expected_dict, response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
