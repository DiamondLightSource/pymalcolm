import unittest

from malcolm.core import call_with_params
from malcolm.modules.builtin.parts import GroupPart


class TestGroupPart(unittest.TestCase):

    def setUp(self):
        self.o = call_with_params(
            GroupPart, name="things", description="A group of things")
        self.setter = list(self.o.create_attribute_models())[0][2]

    def test_init(self):
        assert self.o.name == "things"
        assert self.o.attr.value == "expanded"
        assert self.o.attr.meta.description == "A group of things"
        assert self.o.attr.meta.tags == ("widget:group", "config")

    def test_setter(self):
        assert self.o.attr.value == "expanded"
        self.setter("collapsed")
        assert self.o.attr.value == "collapsed"
        with self.assertRaises(ValueError):
            self.setter("anything else")
