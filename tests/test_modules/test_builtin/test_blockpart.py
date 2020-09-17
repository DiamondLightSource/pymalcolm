import unittest

from malcolm.core import Controller, Process
from malcolm.modules.builtin.parts import BlockPart


class TestBlockPart(unittest.TestCase):
    def setUp(self):
        self.o = BlockPart(name="panda", description="desc")
        self.c = Controller("mri")
        self.c.add_part(self.o)
        self.c.setup(Process("proc"))

    def test_init(self):
        assert self.o.name == "panda"
        assert self.o.attr.value == ""
        assert self.o.attr.meta.description == "desc"
        assert self.o.attr.meta.tags == [
            "widget:textinput",
            "config:1",
            "sinkPort:block:",
        ]
        assert self.c.field_registry.fields[self.o] == [
            ("panda", self.o.attr, self.o.attr.set_value, False)
        ]
