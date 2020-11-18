import unittest

from malcolm.core import Controller, Process
from malcolm.modules.builtin.parts import ChoicePart


class TestChoicePart(unittest.TestCase):
    def setUp(self):
        self.o = ChoicePart(
            name="cp", description="desc", choices=["a", "b"], value="a", writeable=True
        )
        self.c = Controller("mri")
        self.c.add_part(self.o)
        self.c.setup(Process("proc"))

    def test_init(self):
        assert self.o.name == "cp"
        assert self.o.attr.value == "a"
        assert self.o.attr.meta.description == "desc"
        assert self.o.attr.meta.choices == ["a", "b"]
        assert self.o.attr.meta.tags == ["widget:combo", "config:1"]
        assert self.c.field_registry.fields[self.o] == [
            ("cp", self.o.attr, self.o.attr.set_value, False)
        ]

    def test_setter(self):
        assert self.o.attr.value == "a"
        self.o.attr.set_value("b")
        assert self.o.attr.value == "b"
        with self.assertRaises(ValueError):
            self.o.attr.set_value("c")
