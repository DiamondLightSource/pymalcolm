import unittest
from collections import OrderedDict

from malcolm.core.vmetas import ChoiceMeta


class TestInit(unittest.TestCase):
    def test_init(self):
        self.choice_meta = ChoiceMeta(
            "test description", ["a", "b"])
        assert (
            "test description") == self.choice_meta.description
        assert (
            self.choice_meta.typeid) == "malcolm:core/ChoiceMeta:1.0"
        assert (
            self.choice_meta.label) == ""
        assert (
            self.choice_meta.choices) == ("a", "b")


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.choice_meta = ChoiceMeta(
            "test description", ["a", "b"])

    def test_given_valid_value_then_return(self):
        response = self.choice_meta.validate("a")
        assert "a" == response

    def test_int_validate(self):
        response = self.choice_meta.validate(1)
        assert "b" == response

    def test_None_valid(self):
        response = self.choice_meta.validate(None)
        assert "a" == response

    def test_given_invalid_value_then_raises(self):
        with self.assertRaises(ValueError):
            self.choice_meta.validate('badname')

    def test_set_choices(self):
        self.choice_meta.set_choices(["4"])

        assert ("4",) == self.choice_meta.choices


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
        assert bm.to_dict() == self.serialized

    def test_from_dict(self):
        bm = ChoiceMeta.from_dict(self.serialized)
        assert type(bm) == ChoiceMeta
        assert bm.description == "desc"
        assert bm.choices == ("a", "b")
        assert bm.tags == ()
        assert not bm.writeable
        assert bm.label == "name"
