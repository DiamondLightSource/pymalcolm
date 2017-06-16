import unittest

from malcolm.core import call_with_params
from malcolm.modules.builtin.parts import StringPart


class TestStringPart(unittest.TestCase):

    def setUp(self):
        self.o = call_with_params(
            StringPart, name="sp", description="desc",
            widget="textinput")
        self.setter = list(self.o.create_attribute_models())[0][2]

    def test_init(self):
        assert self.o.name == "sp"
        assert self.o.attr.value == ""
        assert self.o.attr.meta.description == "desc"
        assert self.o.attr.meta.tags == ("widget:textinput",)
        assert self.setter is None
