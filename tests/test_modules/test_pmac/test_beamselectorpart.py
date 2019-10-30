
from malcolm.testutil import ChildTestCase

from malcolm.core import Context, Process
from malcolm.modules.pmac.parts import BeamSelectorPart
from malcolm.yamlutil import make_block_creator

from scanpointgenerator import LineGenerator, CompoundGenerator, \
    StaticPointGenerator

class TestBeamSelectorPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        pmac_block = make_block_creator(
            __file__, "test_pmac_manager_block.yaml")
        self.child = self.create_child_block(
            pmac_block, self.process, mri_prefix="PMAC",
            config_dir="/tmp")
        # These are the child blocks we are interested in
        self.child_x = self.process.get_controller("BL45P-ML-STAGE-01:X")
        self.child_y = self.process.get_controller("BL45P-ML-STAGE-01:Y")
        self.child_cs1 = self.process.get_controller("PMAC:CS1")
        self.child_traj = self.process.get_controller("PMAC:TRAJ")
        self.child_status = self.process.get_controller("PMAC:STATUS")
        # CS1 needs to have the right port otherwise we will error
        self.set_attributes(self.child_cs1, port="CS1")
        self.o = BeamSelectorPart(name="pmac", mri="PMAC")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

        pass

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)
        pass

    def set_motor_attributes(
            self, x_pos=0.5, y_pos=0.0, units="mm",
            x_acceleration=2.5, y_acceleration=2.5,
            x_velocity=1.0, y_velocity=1.0):
        # create some parts to mock the motion controller and 2 axes in a CS
        self.set_attributes(
            self.child_x, cs="CS1,A",
            accelerationTime=x_velocity / x_acceleration, resolution=0.001,
            offset=0.0, maxVelocity=x_velocity, readback=x_pos,
            velocitySettle=0.0, units=units)
        self.set_attributes(
            self.child_y, cs="CS1,B",
            accelerationTime=y_velocity / y_acceleration, resolution=0.001,
            offset=0.0, maxVelocity=y_velocity, readback=y_pos,
            velocitySettle=0.0, units=units)

    def do_configure(self, axes_to_scan, completed_steps=0, x_pos=0.5,
                     y_pos=0.0, duration=1.0, units="mm", infos=None):
        self.set_motor_attributes(x_pos, y_pos, units)
        steps_to_do = 3 * len(axes_to_scan)
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], duration)
        generator.prepare()
        self.o.configure(
            self.context, completed_steps, steps_to_do, {"part": infos},
            generator, axes_to_scan)
        pass

    def test_configure(self):
        self.do_configure(axes_to_scan=["x", "y"])
        pass