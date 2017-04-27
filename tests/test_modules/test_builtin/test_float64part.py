import unittest

from malcolm.core import call_with_params
from malcolm.modules.builtin.parts import Float64Part


class TestFloat64Part(unittest.TestCase):

    def setUp(self):
        self.o = call_with_params(
            Float64Part, name="fp", description="desc", initialValue=2.3,
            writeable=True)
        self.setter = list(self.o.create_attributes())[0][2]

    def test_init(self):
        assert self.o.name == "fp"
        assert self.o.attr.value == 2.3
        assert self.o.attr.meta.description == "desc"
        assert self.o.attr.meta.dtype == "float64"

    def test_setter(self):
        assert self.o.attr.value == 2.3
        self.setter(3)
        assert self.o.attr.value == 3.0
        self.assertRaises(ValueError, self.setter, "c")
