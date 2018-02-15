import unittest

from malcolm.core import Part


class TestPart(unittest.TestCase):
    def test_init(self):
        p = Part("name")
        assert p.name == "name"
