#!/bin/env dls-python

import unittest
from collections import OrderedDict

from malcolm.core.mapmeta import MapMeta

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from pkg_resources import require
require("mock")
from mock import MagicMock


class TestInit(unittest.TestCase):

    def setUp(self):
        self.meta_map = MapMeta("Test")

    def test_values_set(self):
        self.assertEqual(self.meta_map.name, "Test")
        self.assertIsInstance(self.meta_map.elements, OrderedDict)
        self.assertEqual(self.meta_map.elements, {})


class TestAddElement(unittest.TestCase):

    def setUp(self):
        self.meta_map = MapMeta("Test")
        self.attribute_mock = MagicMock()

    def test_given_valid_required_element_then_add(self):
        self.meta_map.add_element(self.attribute_mock, required=True)

        self.assertEqual(self.attribute_mock,
                         self.meta_map.elements[self.attribute_mock.name])
        self.assertEqual(True, self.meta_map.required[0])

    def test_given_valid_optional_element_then_add(self):
        self.meta_map.add_element(self.attribute_mock, required=False)

        self.assertEqual(self.attribute_mock,
                         self.meta_map.elements[self.attribute_mock.name])
        self.assertEqual(False, self.meta_map.required[0])

    def test_given_existing_element_then_raise_error(self):
        self.meta_map.add_element(self.attribute_mock, required=False)
        expected_error_message = "Element already exists in dictionary"

        with self.assertRaises(ValueError) as error:
            self.meta_map.add_element(self.attribute_mock, required=False)

        self.assertEqual(expected_error_message, error.exception.message)

if __name__ == "__main__":
    unittest.main(verbosity=2)
