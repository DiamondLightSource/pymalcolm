import unittest

from malcolm.core import Controller, Process
from malcolm.modules.builtin.parts import GroupPart


class TestGroupPart(unittest.TestCase):
    def setUp(self):
        self.o = GroupPart(name="things", description="A group of things")
        self.c = Controller("mri")
        self.c.add_part(self.o)
        self.c.setup(Process("proc"))

    def test_init(self):
        assert self.o.name == "things"
        assert self.o.attr.value == "expanded"
        assert self.o.attr.meta.description == "A group of things"
        assert self.o.attr.meta.tags == ["widget:group", "config:1"]
        assert self.c.field_registry.fields[self.o] == [
            ("things", self.o.attr, self.o.attr.set_value, False)
        ]

    def test_setter(self):
        assert self.o.attr.value == "expanded"
        self.o.attr.set_value("collapsed")
        assert self.o.attr.value == "collapsed"
        with self.assertRaises(ValueError):
            self.o.attr.set_value("anything else")
