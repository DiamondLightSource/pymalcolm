import os
import sys
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths
import unittest

from malcolm.core.choicearraymeta import ChoiceArrayMeta


class TestChoiceArrayMeta(unittest.TestCase):

    def setUp(self):
        self.meta = ChoiceArrayMeta("test_meta", "test description", [1, 2, 3])

    def test_init(self):
        self.assertEqual("test_meta", self.meta.name)
        self.assertEqual("test description", self.meta.description)
        self.assertEqual(self.meta.label, "test_meta")
        self.assertEqual(self.meta.typeid, "malcolm:core/ChoiceArrayMeta:1.0")
        self.assertEqual(self.meta.choices, [1, 2, 3])

    def test_validate_none(self):
        self.assertIsNone(self.meta.validate(None))

    def test_validate(self):
        response = self.meta.validate([2, 3])

        self.assertEqual([2, 3], response)

    def test_not_iterable_raises(self):
        value = 1
        self.assertRaises(ValueError, self.meta.validate, value)

    def test_null_element_raises(self):
        array = [1, None]
        self.assertRaises(ValueError, self.meta.validate, array)

    def test_invalid_choice_raises(self):
        with self.assertRaises(ValueError):
            self.meta.validate([2, 0])

    def test_to_dict(self):
        expected = OrderedDict()
        expected["typeid"] = "malcolm:core/ChoiceArrayMeta:1.0"
        expected['choices'] = [1, 2, 3]
        expected["description"] = "test description"
        expected["tags"] = []
        expected["writeable"] = True
        expected["label"] = "test_meta"
        self.assertEqual(expected, self.meta.to_dict())

    def test_from_dict(self):
        d = OrderedDict()
        d['choices'] = [1, 2, 3]
        d["description"] = "test array description"
        d["tags"] = ["tag"]
        d["writeable"] = False
        d["label"] = "test_label"

        s = ChoiceArrayMeta.from_dict("test_array_meta", d)

        self.assertEqual(ChoiceArrayMeta, type(s))
        self.assertEqual(s.name, "test_array_meta")
        self.assertEqual(s.description, "test array description")
        self.assertEqual(s.tags, ["tag"])
        self.assertEqual(s.writeable, False)
        self.assertEqual(s.label, "test_label")


if __name__ == "__main__":
    unittest.main()
