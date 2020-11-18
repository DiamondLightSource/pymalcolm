import unittest

from malcolm.core import Controller, Process
from malcolm.modules.builtin.parts import HelpPart


class TestHelpPart(unittest.TestCase):
    def setUp(self):
        self.o = HelpPart(help_url="/BLOCK.html")
        self.c = Controller("mri")
        self.c.add_part(self.o)
        self.c.setup(Process("proc"))

    def test_init(self):
        assert self.o.name == "help"
        assert self.o.attr.value == "/BLOCK.html"
        assert self.o.attr.meta.tags == ["widget:help"]
        assert self.c.field_registry.fields[self.o] == [
            ("help", self.o.attr, None, False)
        ]
