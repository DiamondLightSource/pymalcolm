import unittest

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.modules.scanning.parts import SimultaneousAxesPart


class TestSimultaneousAxesPart(unittest.TestCase):

    def setUp(self):
        self.o = SimultaneousAxesPart(value=["x", "y"])

    def test_good(self):
        gen = self.make_generator()
        self.o.validate(gen)

    def test_bad(self):
        self.o.attr.set_value(["x", "z"])
        gen = self.make_generator()
        with self.assertRaises(AssertionError):
            self.o.validate(gen)

    def make_generator(self):
        line1 = LineGenerator('y', 'mm', 0, 2, 3)
        line2 = LineGenerator('x', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [])
        return compound
