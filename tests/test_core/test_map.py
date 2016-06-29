import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock

# module imports
from malcolm.core.map import Map


class TestMap(unittest.TestCase):

    def setUp(self):
        self.meta = MagicMock()
        self.meta.elements.keys.return_value = ["name", "description"]
        d = dict(name="Test", description="Tests")
        self.map = Map(self.meta, d)

    def test_init(self):
        self.assertEqual(self.meta, self.map._meta)
        self.assertEqual("Test", self.map.name)
        self.assertEqual("Tests", self.map.description)

    def test_init_raises(self):
        with self.assertRaises(KeyError):
            Map(self.meta, dict(invalid_key=None))

    def test_get_attr(self):

        response = self.map.name

        self.assertEqual("Test", response)

    def test_get_attr_raises(self):
        with self.assertRaises(AttributeError):
            self.map.none

    def test_set_attr(self):
        self.map.name = "Test2"

        self.assertEqual("Test2", self.map['name'])

    def test_set_attr_raises(self):
        with self.assertRaises(KeyError):
            self.map.none = "Test2"

