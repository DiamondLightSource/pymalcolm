import unittest

from malcolm.core.vmetas import BooleanArrayMeta


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.meta = BooleanArrayMeta("test description")

    def test_init(self):
        assert "test description" == self.meta.description
        assert self.meta.label == ""
        assert self.meta.typeid == "malcolm:core/BooleanArrayMeta:1.0"

    def test_validate_none(self):
        assert list(self.meta.validate(None)) == []

    def test_validate_array(self):
        array = ["True", "", True, False, 1, 0]
        assert (
            [True, False, True, False, True, False]) == (
            list(self.meta.validate(array)))

    def test_not_iterable_raises(self):
        value = True
        with self.assertRaises(TypeError):
            self.meta.validate(value)

    def test_null_element_raises(self):
        array = ["test", None]
        assert (
            [True, False]) == list(self.meta.validate(array))
