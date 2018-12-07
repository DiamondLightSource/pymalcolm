from malcolm.core import Context, Process
from malcolm.modules.pmac.parts import MotorPart
from malcolm.modules.pmac.blocks import compound_motor_block
from malcolm.testutil import ChildTestCase


class TestCompoundPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        child = self.create_child_block(
            compound_motor_block, self.process, mri="my_mri", prefix="PV:PRE")
        self.set_attributes(child,
                            maxVelocity=5.0,
                            accelerationTime=0.5,
                            readback=12.3,
                            offset=4.5,
                            resolution=0.001,
                            cs="CS_PORT,B")
        self.o = MotorPart(name="scan", mri="my_mri")
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_report(self):
        returns = self.o.report_status(self.context)
        assert returns.cs_axis == "B"
        assert returns.cs_port == "CS_PORT"
        assert returns.acceleration == 10.0
        assert returns.resolution == 0.001
        assert returns.offset == 4.5
        assert returns.max_velocity == 5.0
        assert returns.current_position == 12.3
        assert returns.scannable == "scan"
