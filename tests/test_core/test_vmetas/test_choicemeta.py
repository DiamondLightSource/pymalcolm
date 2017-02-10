import sys
import os
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import setup_malcolm_paths

from malcolm.core.vmetas import ChoiceMeta


class TestInit(unittest.TestCase):
    def test_init(self):
        self.choice_meta = ChoiceMeta(
            "test description", ["a", "b"])
        self.assertEqual(
            "test description", self.choice_meta.description)
        self.assertEqual(
            self.choice_meta.typeid, "malcolm:core/ChoiceMeta:1.0")
        self.assertEqual(
            self.choice_meta.label, "")
        self.assertEqual(
            self.choice_meta.choices, ("a", "b"))


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.choice_meta = ChoiceMeta(
            "test description", ["a", "b"])

    def test_given_valid_value_then_return(self):
        response = self.choice_meta.validate("a")
        self.assertEqual("a", response)

    def test_int_validate(self):
        response = self.choice_meta.validate(1)
        self.assertEqual("b", response)

    def test_None_valid(self):
        response = self.choice_meta.validate(None)
        self.assertEqual("a", response)

    def test_given_invalid_value_then_raises(self):
        with self.assertRaises(ValueError):
            self.choice_meta.validate('badname')

    def test_set_choices(self):
        self.choice_meta.set_choices(["4"])

        self.assertEqual(("4",), self.choice_meta.choices)


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "malcolm:core/ChoiceMeta:1.0"
        self.serialized["description"] = "desc"
        self.serialized["choices"] = ("a", "b")
        self.serialized["tags"] = ()
        self.serialized["writeable"] = False
        self.serialized["label"] = "name"

    def test_to_dict(self):
        bm = ChoiceMeta("desc", ["a", "b"], label="name")
        self.assertEqual(bm.to_dict(), self.serialized)

    def test_from_dict(self):
        bm = ChoiceMeta.from_dict(self.serialized)
        self.assertEqual(type(bm), ChoiceMeta)
        self.assertEquals(bm.description, "desc")
        self.assertEquals(bm.choices, ("a", "b"))
        self.assertEqual(bm.tags, ())
        self.assertFalse(bm.writeable)
        self.assertEqual(bm.label, "name")


if __name__ == "__main__":
    unittest.main(verbosity=2)
