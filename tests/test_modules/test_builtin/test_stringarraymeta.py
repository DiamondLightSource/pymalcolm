import unittest

from malcolm.modules.builtin.vmetas import StringArrayMeta


class TestStringArrayMeta(unittest.TestCase):

    def setUp(self):
        self.meta = StringArrayMeta("test description")

    def test_init(self):
        self.assertEqual("test description", self.meta.description)
        self.assertEqual(self.meta.label, "")
        self.assertEqual(self.meta.typeid, "malcolm:core/StringArrayMeta:1.0")

    def test_validate_none(self):
        self.assertEquals(self.meta.validate(None), ())

    def test_validate_array(self):
        array = ["test_string", 123, 123.456]
        self.assertRaises(ValueError, self.meta.validate, array)

    def test_not_iterable_raises(self):
        value = 12346
        self.assertRaises(TypeError, self.meta.validate, value)

    def test_null_element_raises(self):
        array = ["test", None]
        self.assertRaises(ValueError, self.meta.validate, array)
