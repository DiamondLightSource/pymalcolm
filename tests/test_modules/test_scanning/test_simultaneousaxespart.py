import unittest

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Process
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.parts import SimultaneousAxesPart


def make_generator():
    line1 = LineGenerator('y', 'mm', 0, 2, 3)
    line2 = LineGenerator('x', 'mm', 0, 2, 2)
    compound = CompoundGenerator([line1, line2], [], [])
    return compound


class TestSimultaneousAxesPart(unittest.TestCase):

    def setUp(self):
        self.o = SimultaneousAxesPart(value=["x", "y"])

    def test_controller(self):
        self.process = Process("proc")
        self.process.start()
        self.addCleanup(self.process.stop, 2)
        c = RunnableController("mri", "/tmp")
        c.add_part(self.o)
        self.process.add_controller(c)
        b = c.make_view()
        b.simultaneousAxes.put_value(["x", "z"])
        with self.assertRaises(AssertionError):
            b.validate(make_generator())

    def test_good(self):
        gen = make_generator()
        self.o.validate(gen)

    def test_bad(self):
        self.o.attr.set_value(["x", "z"])
        gen = make_generator()
        with self.assertRaises(AssertionError):
            self.o.validate(gen)
