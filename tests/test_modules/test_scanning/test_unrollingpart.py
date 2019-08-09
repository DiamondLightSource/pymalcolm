import unittest

from annotypes import json_encode
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
        assert json_encode(generator, indent=2) == """{
  "typeid": "scanpointgenerator:generator/CompoundGenerator:1.0", 
  "generators": [
    {
      "typeid": "scanpointgenerator:generator/LineGenerator:1.0", 
      "axes": [
        "y"
      ], 
      "units": [
        "mm"
      ], 
      "start": [
        0
      ], 
      "stop": [
        2
      ], 
      "size": 3, 
      "alternate": false
    }, 
    {
      "typeid": "scanpointgenerator:generator/LineGenerator:1.0", 
      "axes": [
        "x"
      ], 
      "units": [
        "mm"
      ], 
      "start": [
        0
      ], 
      "stop": [
        2
      ], 
      "size": 2, 
      "alternate": true
    }
  ], 
  "excluders": [
    {
      "typeid": "scanpointgenerator:excluder/SquashingExcluder:1.0", 
      "axes": [
        "x", 
        "y"
      ]
    }
  ], 
  "mutators": [], 
  "duration": -1.0, 
  "continuous": true
}"""