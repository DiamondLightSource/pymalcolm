import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest

from malcolm.core import call_with_params
from malcolm.parts.builtin import ChoicePart


class TestChoicePart(unittest.TestCase):

    def setUp(self):
        self.o = call_with_params(
            ChoicePart, name="cp", description="desc", choices=["a", "b"],
            initialValue="a", writeable=True)
        self.setter = list(self.o.create_attributes())[0][2]

    def test_init(self):
        assert self.o.name == "cp"
        assert self.o.attr.value == "a"
        assert self.o.attr.meta.description == "desc"
        assert self.o.attr.meta.choices == ("a", "b")

    def test_setter(self):
        assert self.o.attr.value == "a"
        self.setter("b")
        assert self.o.attr.value == "b"
        self.assertRaises(ValueError, self.setter, "c")


if __name__ == "__main__":
    unittest.main(verbosity=2)