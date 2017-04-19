import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest

from malcolm.core import call_with_params
from malcolm.modules.builtin.parts import StringPart


class TestStringPart(unittest.TestCase):

    def setUp(self):
        self.o = call_with_params(
            StringPart, name="sp", description="desc", config=True,
            widget="textinput")
        self.setter = list(self.o.create_attributes())[0][2]

    def test_init(self):
        assert self.o.name == "sp"
        assert self.o.attr.value == ""
        assert self.o.attr.meta.description == "desc"
        assert self.o.attr.meta.tags == ("widget:textinput", "config")
        assert self.setter is None


if __name__ == "__main__":
    unittest.main(verbosity=2)