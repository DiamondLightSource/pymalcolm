import unittest

from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import Process
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.parts import SimultaneousAxesPart


def make_generator():
    line1 = LineGenerator("y", "mm", 0, 2, 3)
    line2 = LineGenerator("x", "mm", 0, 2, 2)
    compound = CompoundGenerator([line1, line2], [], [])
    return compound


class TestSimultaneousAxesPart(unittest.TestCase):
    def setUp(self):
        self.o = SimultaneousAxesPart(value=["x", "y"])
        self.process = Process("proc")
        self.process.start()
        self.addCleanup(self.process.stop, 2)
        c = RunnableController("mri", "/tmp")
        c.add_part(self.o)
        self.process.add_controller(c)
        self.b = c.block_view()

    def test_good(self):
        self.b.simultaneousAxes.put_value(["x", "y"])
        self.b.validate(make_generator(), ["x", "y"])

    def test_bad(self):
        self.b.simultaneousAxes.put_value(["x", "z"])
        with self.assertRaises(AssertionError):
            self.b.validate(make_generator(), ["x", "y"])
