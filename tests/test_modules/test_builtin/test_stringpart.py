import unittest

from malcolm.core import Controller, Process
from malcolm.modules.builtin.parts import StringPart


class TestStringPart(unittest.TestCase):
    def setUp(self):
        self.o = StringPart(name="sp", description="desc")
        self.c = Controller("mri")
        self.c.add_part(self.o)
        self.c.setup(Process("proc"))

    def test_init(self):
        assert self.o.name == "sp"
        assert self.o.attr.value == ""
        assert self.o.attr.meta.description == "desc"
        assert self.o.attr.meta.tags == ["widget:textupdate"]
        assert self.c.field_registry.fields[self.o] == [
            ("sp", self.o.attr, None, False)
        ]
