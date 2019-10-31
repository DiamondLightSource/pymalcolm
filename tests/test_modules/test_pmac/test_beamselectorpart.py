
from malcolm.testutil import ChildTestCase

from malcolm.core import Context, Process
from malcolm.modules.pmac.parts import BeamSelectorPart
from malcolm.yamlutil import make_block_creator

from scanpointgenerator import LineGenerator, CompoundGenerator, \
    StaticPointGenerator

import pytest
from mock import call

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
        #xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys], [], [], duration)
        generator.prepare()
        self.o.configure(
            self.context, completed_steps, steps_to_do, {"part": infos},
            generator, axes_to_scan)
        pass

    def do_check_output(self, user_programs=None):
        if user_programs is None:
            user_programs = [
                1, 4, 1, 4, 1, 4, 2, 8, 8, 8, 1, 4, 1, 4, 1, 4, 2, 8
            ]
        # use a slice here because I'm getting calls to __str__ in debugger
        assert self.child.handled_requests.mock_calls[:4] == [
            call.post('writeProfile',
                      csPort='CS1', timeArray=[0.002], userPrograms=[8]),
            call.post('executeProfile'),
            call.post('moveCS1', a=-0.1375, b=0.0, moveTime=1.0375),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post('writeProfile',
                      a=pytest.approx(
                          [-0.125, 0., 0.125, 0.25, 0.375, 0.5, 0.625, 0.6375,
                           0.6375, 0.6375, 0.625, 0.5, 0.375, 0.25, 0.125, 0.,
                           -0.125, -0.1375]),
                      b=pytest.approx(
                          [0., 0., 0., 0., 0., 0., 0., 0.0125, 0.05, 0.0875,
                           0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]),
                      csPort='CS1',
                      timeArray=pytest.approx(
                          [100000, 500000, 500000, 500000, 500000, 500000,
                           500000, 100000, 100000, 100000, 100000, 500000,
                           500000, 500000, 500000, 500000, 500000, 100000]),
                      userPrograms=pytest.approx(user_programs),
                      velocityMode=pytest.approx(
                          [1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0,
                           0, 0, 1, 3])
                      )
        ]
        assert self.o.completed_steps_lookup == [
            0, 0, 1, 1, 2, 2, 3, 3, 3, 3,
            3, 3, 4, 4, 5, 5, 6, 6]


    def test_configure(self):
        self.do_configure(axes_to_scan=["y"])
        self.do_check_output()
