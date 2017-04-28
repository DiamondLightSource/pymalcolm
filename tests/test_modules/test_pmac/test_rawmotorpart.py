from malcolm.core import call_with_params, Context, Process
from malcolm.modules.pmac.parts import RawMotorPart
from malcolm.modules.pmac.blocks import raw_motor_block
from malcolm.testutil import ChildTestCase


class TestRawMotorPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        child = self.create_child_block(
            raw_motor_block, self.process, mri="mri", prefix="PV:PRE",
            motorPrefix="MOT:PRE", scannable="scan")
        child.parts["maxVelocity"].attr.set_value(5.0)
        child.parts["accelerationTime"].attr.set_value(0.5)
        child.parts["position"].attr.set_value(12.3)
        child.parts["offset"].attr.set_value(4.5)
        child.parts["resolution"].attr.set_value(0.001)
        child.parts["csPort"].attr.set_value("CS1")
        child.parts["csAxis"].attr.set_value("Y")
        self.o = call_with_params(RawMotorPart, name="part", mri="mri")
        list(self.o.create_attributes())
        self.process.start()

    def tearDown(self):
        del self.context
        self.process.stop()

    def test_report(self):
        returns = self.o.report_cs_info(self.context)[0]
        self.assertEqual(returns.cs_axis, "Y")
        self.assertEqual(returns.cs_port, "CS1")
        self.assertEqual(returns.acceleration, 10.0)
        self.assertEqual(returns.resolution, 0.001)
        self.assertEqual(returns.offset, 4.5)
        self.assertEqual(returns.max_velocity, 5.0)
        self.assertEqual(returns.current_position, 12.3)
        self.assertEqual(returns.scannable, "scan")
