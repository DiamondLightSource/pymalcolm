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
        self.meta.keys.return_value = ["name", "description"]
        self.meta.elements = dict(test=0)

    def test_init(self):
        d = dict(name="Test", description="Tests")
        self.map = Map(self.meta, d)

        self.assertEqual(self.meta, self.map._meta)
        self.assertEqual("Test", self.map.name)
        self.assertEqual("Tests", self.map.description)

    def test_init_raises(self):
        with self.assertRaises(ValueError):
            Map(self.meta, dict(invalid_key=None))

    def test_get_attr(self):
        self.map = Map(self.meta)
        self.map['test'] = 1

        response = self.map.test

        self.assertEqual(1, response)

    def test_set_attr(self):
        self.map = Map(self.meta)
        self.map.test = 2

        self.assertEqual(2, self.map['test'])

