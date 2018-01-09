import unittest

from malcolm.core.vmetas import ChoiceArrayMeta


class TestInit(unittest.TestCase):
    def test_init(self):
        self.meta = ChoiceArrayMeta("test description", ["a", "b"])
        assert "test description" == self.meta.description
        assert self.meta.label == ""
        assert self.meta.typeid == "malcolm:core/ChoiceArrayMeta:1.0"
        assert self.meta.choices == ("a", "b")


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.meta = ChoiceArrayMeta("test description", ["a", "b"])

    def test_validate_none(self):
        assert self.meta.validate(None) == ()

    def test_validate(self):
        response = self.meta.validate(["b", "a"])
        assert ("b", "a") == response

    def test_not_iterable_raises(self):
        value = "abb"
        with self.assertRaises(ValueError):
            self.meta.validate(value)

    def test_null_element_raises(self):
        array = ["b", None]
        with self.assertRaises(ValueError):
            self.meta.validate(array)

    def test_invalid_choice_raises(self):
        with self.assertRaises(ValueError):
            self.meta.validate(["a", "x"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
