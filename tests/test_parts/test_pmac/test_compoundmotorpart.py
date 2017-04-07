import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock

from malcolm.core import call_with_params, Context
from malcolm.parts.pmac import CompoundMotorPart


class TestRawMotorPart(unittest.TestCase):

    def setUp(self):
        self.o = call_with_params(CompoundMotorPart, name="part", mri="mri")
        self.context = MagicMock(spec=Context)
        self.child = self.context.block_view.return_value
        self.child.maxVelocity = 5.0
        self.child.accelerationTime = 0.5
        self.child.outLink = "@asyn(CS_PORT,2)"

    def test_report(self):
        returns = self.o.report_cs_info(self.context)[0]
        self.assertEqual(returns.cs_axis, "B")
        self.assertEqual(returns.cs_port, "CS_PORT")
        self.assertEqual(returns.acceleration, 10.0)
        self.assertEqual(returns.resolution, 1.0)
        self.assertEqual(returns.offset, self.child.offset)
        self.assertEqual(returns.max_velocity, self.child.maxVelocity)
        self.assertEqual(returns.current_position, self.child.position)
        self.assertEqual(returns.scannable, self.child.scannable)


if __name__ == "__main__":
    unittest.main(verbosity=2)
