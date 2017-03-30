import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, call, ANY

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.parts.demo.scantickerpart import ScanTickerPart


class AlmostFloat:
    def __init__(self, val, delta):
        self.val = val
        self.delta = delta

    def __eq__(self, other):
        return abs(self.val - other) <= self.delta


class TestScanTickerPart(unittest.TestCase):

    def setUp(self):
        self.process = Mock()
        self.child = MagicMock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem
        self.params = ScanTickerPart.MethodMeta.prepare_input_map(
            name="AxisTwo", mri="mri")
        self.process.get_block.return_value = self.child
        self.o = ScanTickerPart(self.process, self.params)

    def prepare_half_run(self):
        line1 = LineGenerator('AxisOne', 'mm', 0, 2, 3)
        line2 = LineGenerator('AxisTwo', 'mm', 0, 2, 2)
        compound = CompoundGenerator([line1, line2], [], [], 1.0)
        params = ScanTickerPart.configure.MethodMeta.prepare_input_map(
            generator=compound, axesToMove=['AxisTwo'])
        params.generator.prepare()
        self.o.configure(MagicMock(), 0, 2, MagicMock(), params)

    def test_configure(self):
        self.prepare_half_run()
        self.assertEqual(self.o.completed_steps, 0)
        self.assertEqual(self.o.steps_to_do, 2)

    def test_run(self):
        self.prepare_half_run()
        task = MagicMock()
        update_completed_steps = MagicMock()
        self.o.run(task, update_completed_steps)
        self.assertEqual(task.mock_calls, [
            call.put(self.child['counter'], 0),
            call.sleep(AlmostFloat(1.0, delta=0.05)),
            call.put(self.child['counter'], 2),
            call.sleep(AlmostFloat(2.0, delta=0.1))])


if __name__ == "__main__":
    unittest.main(verbosity=2)
