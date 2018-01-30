import unittest

from malcolm.core.vmetas import StringMeta


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.string_meta = StringMeta("test string description")

    def test_given_value_str_then_return(self):
        response = self.string_meta.validate("TestValue")

        assert "TestValue" == response

    def test_given_value_int_then_cast_and_return(self):
        response = self.string_meta.validate(15)

        assert "15" == response

    def test_given_value_float_then_cast_and_return(self):
        response = self.string_meta.validate(12.8)

        assert "12.8" == response

    def test_given_value_None_then_return(self):
        response = self.string_meta.validate(None)

        assert "" == response
