#!/bin/env dls-python

import unittest

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
        self.assertEqual(self.meta_map.elements, [])


class TestAddElement(unittest.TestCase):

    def setUp(self):
        self.meta_map = MapMeta("Test")
        self.attribute_mock = MagicMock()

    def test_given_valid_required_element_then_add(self):
        self.meta_map.add_element(self.attribute_mock, required=True)

        self.assertEqual((self.attribute_mock, True), self.meta_map.elements[0])

    def test_given_valid_optional_element_then_add(self):
        self.meta_map.add_element(self.attribute_mock, required=False)

        self.assertEqual((self.attribute_mock, False), self.meta_map.elements[0])

if __name__ == "__main__":
    unittest.main(verbosity=2)
