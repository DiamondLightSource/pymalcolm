import unittest

from scanpointgenerator import LineGenerator, CompoundGenerator, \
    SquashingExcluder

from malcolm.core import Process
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.parts import UnrollingPart


def make_generator(squashed=False):
    line1 = LineGenerator('y', 'mm', 0, 2, 3)
    line2 = LineGenerator('x', 'mm', 0, 2, 2, alternate=True)
    if squashed:
        excluders = [SquashingExcluder(axes=("x", "y"))]
    else:
        excluders = []
    compound = CompoundGenerator([line1, line2], excluders, [])
    return compound


class TestUnrollingPart(unittest.TestCase):

    def setUp(self):
        self.o = UnrollingPart(name="Unroll")
        self.process = Process("proc")
        self.process.start()
        self.addCleanup(self.process.stop, 2)
        c = RunnableController("mri", "/tmp")
        c.add_part(self.o)
        self.process.add_controller(c)
        self.b = c.block_view()

    def test_no_changes_needed_1dim(self):
        generator = make_generator()
        results = self.b.validate(generator, ["x"])
        assert results["generator"] == generator
        generator.prepare()
        assert len(generator.dimensions) == 2

    def test_no_changes_needed_squashed(self):
        generator = make_generator(squashed=True)
        results = self.b.validate(generator, ["x", "y"])
        assert results["generator"] == generator
        generator.prepare()
        assert len(generator.dimensions) == 1

    def test_changes_needed(self):
        results = self.b.validate(make_generator(), ["x", "y"])
        generator = results["generator"]
        generator.prepare()
        assert len(generator.dimensions) == 1
        assert len(generator.excluders) == 1
        excluder = generator.excluders[0]
        assert isinstance(excluder, SquashingExcluder)
        assert excluder.axes == ["x", "y"]
