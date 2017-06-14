import unittest

from malcolm.core import call_with_params
from malcolm.modules.builtin.parts import ChoicePart


class TestChoicePart(unittest.TestCase):

    def setUp(self):
        self.o = call_with_params(
            ChoicePart, name="cp", description="desc", choices=["a", "b"],
            initialValue="a", writeable=True)
        self.setter = list(self.o.create_attributes())[0][2]

    def test_init(self):
        assert self.o.name == "cp"
        assert self.o.attr.value == "a"
        assert self.o.attr.meta.description == "desc"
        assert self.o.attr.meta.choices == ("a", "b")
        assert self.o.attr.meta.tags == ("config",)

    def test_setter(self):
        assert self.o.attr.value == "a"
        self.setter("b")
        assert self.o.attr.value == "b"
        with self.assertRaises(ValueError):
            self.setter("c")
