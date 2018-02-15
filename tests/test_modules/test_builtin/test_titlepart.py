import unittest

from malcolm.core import Process
from malcolm.modules.builtin.controllers import BasicController
from malcolm.modules.builtin.parts import TitlePart


class TestTitlePart(unittest.TestCase):

    def setUp(self):
        self.o = TitlePart(value="My label")
        self.p = Process("proc")
        self.c = BasicController("mri")
        self.c.add_part(self.o)
        self.p.add_controller(self.c)
        self.p.start()
        self.b = self.p.block_view(self.c.mri)

    def tearDown(self):
        self.p.stop(1)

    def test_init(self):
        assert self.o.name == "label"
        assert self.o.attr.value == "My label"
        assert self.o.attr.meta.tags == [
            "widget:title", "config:1"]
        assert self.b.meta.label == "My label"

    def test_setter(self):
        self.b.label.put_value("My label2")
        assert self.b.label.value == "My label2"
        assert self.b.meta.label == "My label2"
