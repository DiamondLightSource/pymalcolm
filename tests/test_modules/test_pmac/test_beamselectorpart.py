# Treat all division as float division even in python2
from __future__ import division

import pytest
from mock import call
from scanpointgenerator import CompoundGenerator, StaticPointGenerator

from malcolm.core import Context, Process
from malcolm.modules.pmac.parts import BeamSelectorPart
from malcolm.modules.pmac.util import MIN_TIME
from malcolm.testutil import ChildTestCase
from malcolm.yamlutil import make_block_creator


class TestBeamSelectorPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        pmac_block = make_block_creator(__file__, "test_pmac_manager_block.yaml")
        self.child = self.create_child_block(
            pmac_block, self.process, mri_prefix="PMAC", config_dir="/tmp"
        )
        # These are the child blocks we are interested in
        self.child_x = self.process.get_controller("BL45P-ML-STAGE-01:X")
        # self.child_y = self.process.get_controller(
        #    "BL45P-ML-STAGE-01:Y")
        self.child_cs1 = self.process.get_controller("PMAC:CS1")
        self.child_traj = self.process.get_controller("PMAC:TRAJ")
        self.child_status = self.process.get_controller("PMAC:STATUS")

        # CS1 needs to have the right port otherwise we will error
        self.set_attributes(self.child_cs1, port="CS1")
        self.o = BeamSelectorPart(
            name="beamSelector",
            mri="PMAC",
            selectorAxis="x",
            tomoAngle=0,
            diffAngle=0.5,
            moveTime=0.5,
        )
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

        pass

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)
        pass

    def set_motor_attributes(
        self, x_pos=0.5, units="deg", x_acceleration=4.0, x_velocity=10.0
    ):
        # create some parts to mock
        # the motion controller and an axis in a CS
        self.set_attributes(
            self.child_x,
            cs="CS1,A",
            accelerationTime=x_velocity / x_acceleration,
            resolution=0.001,
            offset=0.0,
            maxVelocity=x_velocity,
            readback=x_pos,
            velocitySettle=0.0,
            units=units,
        )

    def test_configure_cycle(self):
        self.set_motor_attributes()
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=4.0
        )
        generator.prepare()
        self.o.on_configure(self.context, 0, nCycles, {}, generator, [])

        assert generator.duration == 1.5

        assert self.child.handled_requests.mock_calls == [
            call.post(
                "writeProfile", csPort="CS1", timeArray=[0.002], userPrograms=[8]
            ),
            call.post("executeProfile"),
            call.post("moveCS1", a=-0.125, moveTime=pytest.approx(0.790, abs=1e-3)),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post(
                "writeProfile",
                a=pytest.approx(
                    [0.0, 0.25, 0.5, 0.625, 0.625, 0.5, 0.25, 0.0, -0.125, -0.125, 0.0]
                ),
                csPort="CS1",
                timeArray=pytest.approx(
                    [
                        250000,
                        250000,
                        250000,
                        250000,
                        1000000,
                        250000,
                        250000,
                        250000,
                        250000,
                        1000000,
                        250000,
                    ]
                ),
                userPrograms=pytest.approx([1, 4, 2, 8, 8, 1, 4, 2, 8, 8, 1]),
                velocityMode=pytest.approx([1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 3]),
            ),
        ]
        assert self.o.completed_steps_lookup == [0, 0, 1, 1, 1, 1, 1, 2, 3, 3, 3]

    def test_validate(self):
        generator = CompoundGenerator([StaticPointGenerator(2)], [], [], 0.0102)
        axesToMove = ["x"]
        # servoFrequency() return value
        self.child.handled_requests.post.return_value = 4919.300698316487
        ret = self.o.on_validate(self.context, generator, axesToMove, {})
        expected = 0.010166
        assert ret.value.duration == expected

    def test_critical_exposure(self):
        self.set_motor_attributes()
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.5
        )
        generator.prepare()
        self.o.on_configure(self.context, 0, nCycles, {}, generator, [])

        assert generator.duration == MIN_TIME

        assert self.child.handled_requests.mock_calls == [
            call.post(
                "writeProfile", csPort="CS1", timeArray=[0.002], userPrograms=[8]
            ),
            call.post("executeProfile"),
            call.post("moveCS1", a=-0.125, moveTime=pytest.approx(0.790, abs=1e-3)),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post(
                "writeProfile",
                a=pytest.approx([0.0, 0.25, 0.5, 0.625, 0.5, 0.25, 0.0, -0.125, 0.0]),
                csPort="CS1",
                timeArray=pytest.approx(
                    [
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                    ]
                ),
                userPrograms=pytest.approx([1, 4, 2, 8, 1, 4, 2, 8, 1]),
                velocityMode=pytest.approx([1, 0, 1, 1, 1, 0, 1, 1, 3]),
            ),
        ]

    def test_invalid_parameters(self):
        self.part_under_test = BeamSelectorPart(
            name="beamSelector2",
            mri="PMAC",
            selectorAxis="x",
            tomoAngle="invalid",
            diffAngle=0.5,
            moveTime=0.5,
        )

        self.context.set_notify_dispatch_request(
            self.part_under_test.notify_dispatch_request
        )

        self.set_motor_attributes()
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.5
        )
        generator.prepare()

        self.part_under_test.on_configure(self.context, 0, nCycles, {}, generator, [])

        assert self.part_under_test.tomoAngle == 0.0
        assert self.part_under_test.diffAngle == 0.0
        assert self.part_under_test.move_time == 0.5
