import unittest

from malcolm.core import Controller, Process
from malcolm.modules.builtin.parts import IconPart


class TestIconPart(unittest.TestCase):
    def setUp(self):
        svg_name = "/tmp/test_icon.svg"
        self.svg_text = '<svg><rect width="300" height="100"/></svg>'
        with open(svg_name, "w") as f:
            f.write(self.svg_text)
        self.o = IconPart(svg=svg_name)
        self.c = Controller("mri")
        self.c.add_part(self.o)
        self.c.setup(Process("proc"))

    def test_init(self):
        assert self.o.name == "icon"
        assert self.o.attr.value == self.svg_text
        assert self.o.attr.meta.description == "SVG icon for the Block"
        assert self.o.attr.meta.tags == ["widget:icon"]
        assert self.c.field_registry.fields[self.o] == [
            ("icon", self.o.attr, None, False)
        ]
