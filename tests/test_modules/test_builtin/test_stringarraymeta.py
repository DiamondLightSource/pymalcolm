import unittest

from malcolm.core.vmetas import StringArrayMeta


class TestStringArrayMeta(unittest.TestCase):

    def setUp(self):
        self.meta = StringArrayMeta("test description")

    def test_init(self):
        assert "test description" == self.meta.description
        assert self.meta.label == ""
        assert self.meta.typeid == "malcolm:core/StringArrayMeta:1.0"

    def test_validate_none(self):
        assert self.meta.validate(None) == ()

    def test_validate_array(self):
        array = ["test_string", 123, 123.456]
        with self.assertRaises(ValueError):
            self.meta.validate(array)

    def test_not_iterable_raises(self):
        value = 12346
        with self.assertRaises(TypeError):
            self.meta.validate(value)

    def test_null_element_raises(self):
        array = ["test", None]
        with self.assertRaises(ValueError):
            self.meta.validate(array)
