from malcolm.core import call_with_params, Context, Process
from malcolm.modules.pmac.parts import CompoundMotorPart
from malcolm.modules.pmac.blocks import compound_motor_block
from malcolm.testutil import ChildTestCase


class TestRawMotorPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        child = self.create_child_block(
            compound_motor_block, self.process, mri="my_mri", prefix="PV:PRE",
            scannable="scan")
        child.parts["maxVelocity"].attr.set_value(5.0)
        child.parts["accelerationTime"].attr.set_value(0.5)
        child.parts["position"].attr.set_value(12.3)
        child.parts["offset"].attr.set_value(4.5)
        child.parts["resolution"].attr.set_value(0.001)
        child.parts["outLink"].attr.set_value("@asyn(CS_PORT,2)")
        self.o = call_with_params(CompoundMotorPart, name="part", mri="my_mri")
        list(self.o.create_attribute_models())
        self.process.start()

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)

    def test_report(self):
        returns = self.o.report_cs_info(self.context)[0]
        assert returns.cs_axis == "B"
        assert returns.cs_port == "CS_PORT"
        assert returns.acceleration == 10.0
        assert returns.resolution == 1.0
        assert returns.offset == 4.5
        assert returns.max_velocity == 5.0
        assert returns.current_position == 12.3
        assert returns.scannable == "scan"
