import unittest
from mock import MagicMock

from malcolm.core import call_with_params, Context
from malcolm.modules.pmac.parts import RawMotorPart


class TestRawMotorPart(unittest.TestCase):

    def setUp(self):
        self.o = call_with_params(RawMotorPart, name="part", mri="mri")
        self.context = MagicMock(spec=Context)
        self.child = self.context.block_view.return_value
        self.child.maxVelocity.value = 5.0
        self.child.accelerationTime.value = 0.5

    def test_report(self):
        returns = self.o.report_cs_info(self.context)[0]
        self.assertEqual(returns.cs_axis, self.child.csAxis.value)
        self.assertEqual(returns.cs_port, self.child.csPort.value)
        self.assertEqual(returns.acceleration, 10.0)
        self.assertEqual(returns.resolution, self.child.resolution.value)
        self.assertEqual(returns.offset, self.child.offset.value)
        self.assertEqual(returns.max_velocity, self.child.maxVelocity.value)
        self.assertEqual(returns.current_position, self.child.position.value)
        self.assertEqual(returns.scannable, self.child.scannable.value)
