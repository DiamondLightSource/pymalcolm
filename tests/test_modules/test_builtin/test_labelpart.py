import unittest
from mock import MagicMock

from malcolm.core import call_with_params, Controller, Process
from malcolm.modules.builtin.parts import LabelPart


class TestLabelPart(unittest.TestCase):

    def setUp(self):
        self.o = call_with_params(
            LabelPart, initialValue="My label", group="mygroup")
        self.p = Process("proc")
        self.c = Controller(self.p, "mri", [self.o])
        self.p.add_controller("mri", self.c)
        self.p.start()
        self.b = self.c.block_view()

    def tearDown(self):
        self.p.stop(1)

    def test_init(self):
        assert self.o.name == "label"
        assert self.o.attr.value == "My label"
        assert self.o.attr.meta.tags == (
            "widget:textinput", "config", "group:mygroup")
        assert self.b.meta.label == "My label"

    def test_setter(self):
        self.b.label.put_value("My label2")
        assert self.b.label.value == "My label2"
        assert self.b.meta.label == "My label2"
