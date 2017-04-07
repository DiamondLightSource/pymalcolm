import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call, ANY

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.parts.demo.scantickerpart import ScanTickerPart
from malcolm.core import call_with_params, Context


class AlmostFloat:
    def __init__(self, val, delta):
        self.val = val
        self.delta = delta

    def __eq__(self, other):
        return abs(self.val - other) <= self.delta


class TestScanTickerPart(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock(spec=Context)
        self.o = call_with_params(ScanTickerPart, name="AxisTwo", mri="mri")

    def prepare_half_run(self):
        line1 = LineGenerator('AxisOne', 'mm', 0, 2, 3)
        line2 = LineGenerator('AxisTwo', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], 1.0)
        compound.prepare()
        call_with_params(self.o.configure, ANY, 0, 2, MagicMock(),
                         generator=compound, axesToMove=['AxisTwo'])

    def test_configure(self):
        self.prepare_half_run()
        self.assertEqual(self.o.completed_steps, 0)
        self.assertEqual(self.o.steps_to_do, 2)

    def test_run(self):
        self.prepare_half_run()
        update_completed_steps = MagicMock()
        self.o.run(self.context, update_completed_steps)
        self.assertEqual(self.context.mock_calls, [
            call.block_view("mri"),
            call.block_view().counter.put_value(0),
            call.sleep(AlmostFloat(1.0, delta=0.05)),
            call.block_view().counter.put_value(2),
            call.sleep(AlmostFloat(2.0, delta=0.1))])


if __name__ == "__main__":
    unittest.main(verbosity=2)
