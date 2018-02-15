from malcolm.core import Context, Process
from malcolm.modules.pmac.parts import RawMotorPart
from malcolm.modules.pmac.blocks import raw_motor_block
from malcolm.testutil import ChildTestCase


class TestRawMotorPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        child = self.create_child_block(
            raw_motor_block, self.process, mri="mri", prefix="PV:PRE",
            motor_prefix="MOT:PRE", scannable="scan")
        self.set_attributes(child,
                            maxVelocity=5.0,
                            accelerationTime=0.5,
                            readback=12.3,
                            offset=4.5,
                            resolution=0.001,
                            csPort="CS1",
                            csAxis="Y")
        self.o = RawMotorPart(name="part", mri="mri")
        self.process.start()

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)

    def test_report(self):
        returns = self.o.report_status(self.context)
        assert returns.cs_axis == "Y"
        assert returns.cs_port == "CS1"
        assert returns.acceleration == 10.0
        assert returns.resolution == 0.001
        assert returns.offset == 4.5
        assert returns.max_velocity == 5.0
        assert returns.current_position == 12.3
        assert returns.scannable == "scan"
