import unittest

from malcolm.core.vmetas import BooleanMeta


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.boolean_meta = BooleanMeta("test description")

    def test_given_value_str_then_cast_and_return(self):
        response = self.boolean_meta.validate("TestValue")
        assert response

        response = self.boolean_meta.validate("")
        assert not response

    def test_given_value_int_then_cast_and_return(self):
        response = self.boolean_meta.validate(15)
        assert response

        response = self.boolean_meta.validate(0)
        assert not response

    def test_given_value_boolean_then_cast_and_return(self):
        response = self.boolean_meta.validate(True)
        assert response

        response = self.boolean_meta.validate(False)
        assert not response

    def test_given_value_None_then_return(self):
        response = self.boolean_meta.validate(None)

        assert False == response
