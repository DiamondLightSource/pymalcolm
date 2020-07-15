import unittest

from malcolm.core import Controller, Process
from malcolm.modules.builtin.parts import Float64Part


class TestFloat64Part(unittest.TestCase):
    def setUp(self):
        self.o = Float64Part(name="fp", description="desc", value=2.3, writeable=True)
        self.c = Controller("mri")
        self.c.add_part(self.o)
        self.c.setup(Process("proc"))

    def test_init(self):
        assert self.o.name == "fp"
        assert self.o.attr.value == 2.3
        assert self.o.attr.meta.description == "desc"
        assert self.o.attr.meta.dtype == "float64"
        assert self.o.attr.meta.tags == ["widget:textinput", "config:1"]
        assert self.c.field_registry.fields[self.o] == [
            ("fp", self.o.attr, self.o.attr.set_value, False)
        ]
