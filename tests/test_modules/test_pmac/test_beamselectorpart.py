import shutil

import pytest
from mock import call
from scanpointgenerator import CompoundGenerator, LineGenerator, StaticPointGenerator

from malcolm.core import Context, Process
from malcolm.modules.builtin.defines import tmp_dir
from malcolm.modules.pmac.parts import BeamSelectorPart
from malcolm.modules.pmac.util import MIN_TIME
from malcolm.modules.scanning.util import DetectorTable
from malcolm.testutil import ChildTestCase
from malcolm.yamlutil import make_block_creator


class TestBeamSelectorPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.config_dir = tmp_dir("config_dir")
        pmac_block = make_block_creator(__file__, "test_pmac_manager_block.yaml")
        self.child = self.create_child_block(
            pmac_block,
            self.process,
            mri_prefix="PMAC",
            config_dir=self.config_dir.value,
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
        self.move_time = 0.5
        self.o = BeamSelectorPart(
            name="beamSelector",
            mri="PMAC",
            selector_axis="x",
            imaging_angle=0,
            diffraction_angle=0.5,
            imaging_detector="imagingDetector",
            diffraction_detector="diffDetector",
            move_time=self.move_time,
        )
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

        pass

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)
        shutil.rmtree(self.config_dir.value)

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

    def _get_detector_table(self, imaging_exposure_time, diffraction_exposure_time):
        return DetectorTable(
            [True, True, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [1, 1, 2],
        )

    def test_validate_returns_tweaked_generator_duration(self):
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 0.1
        diffraction_exposure_time = 0.3
        detectors = self._get_detector_table(
            imaging_exposure_time, diffraction_exposure_time
        )

        # First pass we should tweak
        infos = self.o.on_validate(generator, {}, detectors)

        self.assertEqual(infos.parameter, "generator")
        assert infos.value.duration == pytest.approx(
            self.move_time * 2 + imaging_exposure_time + diffraction_exposure_time
        )

        # Now re-run with our tweaked generator
        infos = self.o.on_validate(infos.value, {}, detectors)
        assert infos is None, "We shouldn't need to tweak again"

    def test_validate_raises_AssertionError_for_bad_generator_type(self):
        line_generator = LineGenerator("x", "mm", 0.0, 5.0, 10)
        generator = CompoundGenerator([line_generator], [], [], duration=0.0)
        imaging_exposure_time = 0.1
        diffraction_exposure_time = 0.3
        detectors = self._get_detector_table(
            imaging_exposure_time, diffraction_exposure_time
        )

        self.assertRaises(AssertionError, self.o.on_validate, generator, {}, detectors)

    def test_validate_raises_ValueError_for_detector_with_invalid_frames_per_step(self):
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 0.1
        diffraction_exposure_time = 0.3
        bad_imaging_frames_per_step = DetectorTable(
            [True, True, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [3, 1, 2],
        )

        bad_diffraction_frames_per_step = DetectorTable(
            [True, True, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [1, 10, 2],
        )

        self.assertRaises(
            ValueError, self.o.on_validate, generator, {}, bad_imaging_frames_per_step
        )
        self.assertRaises(
            ValueError,
            self.o.on_validate,
            generator,
            {},
            bad_diffraction_frames_per_step,
        )

    def test_validate_raises_ValueError_when_detector_not_enabled(self):
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 0.1
        diffraction_exposure_time = 0.3
        detectors_with_imaging_disabled = DetectorTable(
            [False, True, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [1, 1, 2],
        )

        detectors_with_diffraction_disabled = DetectorTable(
            [True, False, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [1, 1, 2],
        )

        self.assertRaises(
            ValueError,
            self.o.on_validate,
            generator,
            {},
            detectors_with_imaging_disabled,
        )
        self.assertRaises(
            ValueError,
            self.o.on_validate,
            generator,
            {},
            detectors_with_diffraction_disabled,
        )

    def test_validate_raises_ValueError_for_detector_with_zero_exposure(self):
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 0.1
        diffraction_exposure_time = 0.3
        detectors_with_zero_exposure_for_imaging = self._get_detector_table(
            0.0, diffraction_exposure_time
        )
        detectors_with_zero_exposure_for_diffraction = self._get_detector_table(
            imaging_exposure_time, 0.0
        )

        self.assertRaises(
            ValueError,
            self.o.on_validate,
            generator,
            {},
            detectors_with_zero_exposure_for_imaging,
        )
        self.assertRaises(
            ValueError,
            self.o.on_validate,
            generator,
            {},
            detectors_with_zero_exposure_for_diffraction,
        )

    def test_validate_raises_ValueError_for_missing_detector(self):
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 0.1
        diffraction_exposure_time = 0.3
        table_without_imaging_detector = DetectorTable(
            [True, True],
            ["diffDetector", "PandA"],
            ["ML-DIFF-01", "ML-PANDA-01"],
            [diffraction_exposure_time, 0.0],
            [1, 2],
        )

        table_without_diffraction_detector = DetectorTable(
            [True, True],
            ["imagingDetector", "PandA"],
            ["ML-IMAGING-01", "ML-PANDA-01"],
            [imaging_exposure_time, 0.0],
            [1, 2],
        )

        self.assertRaises(
            ValueError,
            self.o.on_validate,
            generator,
            {},
            table_without_imaging_detector,
        )
        self.assertRaises(
            ValueError,
            self.o.on_validate,
            generator,
            {},
            table_without_diffraction_detector,
        )

    def test_configure_with_one_cycle(self):
        self.o.imaging_angle = 50.0
        self.o.diffraction_angle = 90.0
        self.set_motor_attributes(x_pos=50.0, x_velocity=800.0, x_acceleration=100000.0)
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 0.1
        diffraction_exposure_time = 0.3
        detectors = self._get_detector_table(
            imaging_exposure_time, diffraction_exposure_time
        )
        # Update generator duration based on validate method
        infos = self.o.on_validate(generator, {}, detectors)
        generator.duration = infos.value.duration
        generator.prepare()

        # Run configure
        self.o.on_configure(self.context, 0, nCycles, {}, generator, detectors, [])

        # Expected generator duration is sum of exposure times + 2*move_time
        assert generator.duration == pytest.approx(
            self.move_time * 2 + imaging_exposure_time + diffraction_exposure_time
        )

        # Build up our expected values
        diffraction_detector_time_row = [2000, 250000, 250000, 2000, 300000]
        imaging_detector_time_row = [2000, 250000, 250000, 2000, 100000]
        times = nCycles * (
            diffraction_detector_time_row + imaging_detector_time_row
        ) + [2000]
        diffraction_velocity_row = [1, 0, 1, 1, 1]
        imaging_velocity_row = [1, 0, 1, 1, 1]
        velocity_modes = nCycles * (diffraction_velocity_row + imaging_velocity_row) + [
            3
        ]
        diffraction_detector_program_row = [1, 4, 2, 8, 8]
        imaging_detector_program_row = [1, 4, 2, 8, 8]
        user_programs = nCycles * (
            diffraction_detector_program_row + imaging_detector_program_row
        ) + [1]
        diffraction_detector_pos_row = [50.0, 70.0, 90.0, 90.08, 90.08]
        imaging_detector_pos_row = [90.0, 70.0, 50.0, 49.92, 49.92]
        positions = nCycles * (
            diffraction_detector_pos_row + imaging_detector_pos_row
        ) + [50.0]
        completed_steps = [0, 0, 1, 1, 1, 1, 1, 2, 3, 3, 3]

        assert self.child.handled_requests.mock_calls == [
            call.post(
                "writeProfile", csPort="CS1", timeArray=[0.002], userPrograms=[8]
            ),
            call.post("executeProfile"),
            call.post("moveCS1", moveTime=0.0017888544, a=49.92),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post(
                "writeProfile",
                csPort="CS1",
                timeArray=pytest.approx(times),
                velocityMode=pytest.approx(velocity_modes),
                userPrograms=pytest.approx(user_programs),
                a=pytest.approx(positions),
            ),
        ]
        assert self.o.completed_steps_lookup == completed_steps

    def test_configure_with_three_cycles(self):
        self.o.imaging_angle = 50.0
        self.o.diffraction_angle = 90.0
        self.set_motor_attributes(x_pos=50.0, x_velocity=800.0, x_acceleration=100000.0)
        nCycles = 3
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 0.1
        diffraction_exposure_time = 0.3
        detectors = self._get_detector_table(
            imaging_exposure_time, diffraction_exposure_time
        )

        # Update generator duration based on validate method
        infos = self.o.on_validate(generator, {}, detectors)
        generator.duration = infos.value.duration
        generator.prepare()

        # Run configure
        self.o.on_configure(self.context, 0, nCycles, {}, generator, detectors, [])

        # Expected generator duration is sum of exposure times + 2*move_time
        assert generator.duration == pytest.approx(
            self.move_time * 2 + imaging_exposure_time + diffraction_exposure_time
        )

        # Build up our expected values
        diffraction_detector_time_row = [2000, 250000, 250000, 2000, 300000]
        imaging_detector_time_row = [2000, 250000, 250000, 2000, 100000]
        times = nCycles * (
            diffraction_detector_time_row + imaging_detector_time_row
        ) + [2000]
        diffraction_velocity_row = [1, 0, 1, 1, 1]
        imaging_velocity_row = [1, 0, 1, 1, 1]
        velocity_modes = nCycles * (diffraction_velocity_row + imaging_velocity_row) + [
            3
        ]
        diffraction_detector_program_row = [1, 4, 2, 8, 8]
        imaging_detector_program_row = [1, 4, 2, 8, 8]
        user_programs = nCycles * (
            diffraction_detector_program_row + imaging_detector_program_row
        ) + [1]
        diffraction_detector_pos_row = [50.0, 70.0, 90.0, 90.08, 90.08]
        imaging_detector_pos_row = [90.0, 70.0, 50.0, 49.92, 49.92]
        positions = nCycles * (
            diffraction_detector_pos_row + imaging_detector_pos_row
        ) + [50.0]
        completed_steps = [
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            2,
            2,
            2,
            2,
            2,
            3,
            3,
            3,
            3,
            3,
            4,
            4,
            4,
            4,
            4,
            5,
            5,
            5,
            5,
            5,
            6,
            7,
            7,
            7,
        ]

        assert self.child.handled_requests.mock_calls == [
            call.post(
                "writeProfile", csPort="CS1", timeArray=[0.002], userPrograms=[8]
            ),
            call.post("executeProfile"),
            call.post("moveCS1", moveTime=0.0017888544, a=49.92),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post(
                "writeProfile",
                csPort="CS1",
                timeArray=pytest.approx(times),
                velocityMode=pytest.approx(velocity_modes),
                userPrograms=pytest.approx(user_programs),
                a=pytest.approx(positions),
            ),
        ]
        assert self.o.completed_steps_lookup == completed_steps

    def test_configure_with_one_cycle_with_long_exposure(self):
        self.o.imaging_angle = 35.0
        self.o.diffraction_angle = 125.0
        self.set_motor_attributes(x_pos=35.0, x_velocity=800.0, x_acceleration=100000.0)
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 4.0
        diffraction_exposure_time = 10.0
        detectors = self._get_detector_table(
            imaging_exposure_time, diffraction_exposure_time
        )
        # Update generator duration based on validate method
        infos = self.o.on_validate(generator, {}, detectors)
        generator.duration = infos.value.duration
        generator.prepare()

        # Run configure
        self.o.on_configure(self.context, 0, nCycles, {}, generator, detectors, [])

        # Expected generator duration is sum of exposure times + 2*move_time
        assert (
            generator.duration
            == self.move_time * 2 + imaging_exposure_time + diffraction_exposure_time
        )

        # Build up our expected values
        diffraction_detector_time_row = [
            2000,
            250000,
            250000,
            2000,
            3333333,
            3333334,
            3333333,
        ]
        imaging_detector_time_row = [2000, 250000, 250000, 2000, 4000000]
        times = nCycles * (
            diffraction_detector_time_row + imaging_detector_time_row
        ) + [2000]
        diffraction_velocity_row = [1, 0, 1, 1, 0, 0, 1]
        imaging_velocity_row = [1, 0, 1, 1, 1]
        velocity_modes = nCycles * (diffraction_velocity_row + imaging_velocity_row) + [
            3
        ]
        diffraction_detector_program_row = [1, 4, 2, 8, 0, 0, 8]
        imaging_detector_program_row = [1, 4, 2, 8, 8]
        user_programs = nCycles * (
            diffraction_detector_program_row + imaging_detector_program_row
        ) + [1]
        diffraction_detector_pos_row = [
            35.0,
            80.0,
            125.0,
            125.18,
            125.18,
            125.18,
            125.18,
        ]
        imaging_detector_pos_row = [125.0, 80.0, 35.0, 34.82, 34.82]
        positions = nCycles * (
            diffraction_detector_pos_row + imaging_detector_pos_row
        ) + [35.0]
        completed_steps = [0, 0, 1, 1, 1, 1, 1, 1, 1, 2, 3, 3, 3]

        assert self.child.handled_requests.mock_calls == [
            call.post(
                "writeProfile", csPort="CS1", timeArray=[0.002], userPrograms=[8]
            ),
            call.post("executeProfile"),
            call.post("moveCS1", moveTime=0.0026832816, a=34.82),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post(
                "writeProfile",
                csPort="CS1",
                timeArray=pytest.approx(times),
                velocityMode=pytest.approx(velocity_modes),
                userPrograms=pytest.approx(user_programs),
                a=pytest.approx(positions),
            ),
        ]
        assert self.o.completed_steps_lookup == completed_steps

    def test_configure_with_three_cycles_with_long_exposure(self):
        self.o.imaging_angle = 35.0
        self.o.diffraction_angle = 125.0
        self.set_motor_attributes(x_pos=35.0, x_velocity=800.0, x_acceleration=100000.0)
        nCycles = 3
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 4.0
        diffraction_exposure_time = 10.0
        detectors = self._get_detector_table(
            imaging_exposure_time, diffraction_exposure_time
        )
        # Update generator duration based on validate method
        infos = self.o.on_validate(generator, {}, detectors)
        generator.duration = infos.value.duration
        generator.prepare()

        # Run configure
        self.o.on_configure(self.context, 0, nCycles, {}, generator, detectors, [])

        # Expected generator duration is sum of exposure times + 2*move_time
        assert (
            generator.duration
            == self.move_time * 2 + imaging_exposure_time + diffraction_exposure_time
        )

        # Build up our expected values
        diffraction_detector_time_row = [
            2000,
            250000,
            250000,
            2000,
            3333333,
            3333334,
            3333333,
        ]
        imaging_detector_time_row = [2000, 250000, 250000, 2000, 4000000]
        times = nCycles * (
            diffraction_detector_time_row + imaging_detector_time_row
        ) + [2000]
        diffraction_velocity_row = [1, 0, 1, 1, 0, 0, 1]
        imaging_velocity_row = [1, 0, 1, 1, 1]
        velocity_modes = nCycles * (diffraction_velocity_row + imaging_velocity_row) + [
            3
        ]
        diffraction_detector_program_row = [1, 4, 2, 8, 0, 0, 8]
        imaging_detector_program_row = [1, 4, 2, 8, 8]
        user_programs = nCycles * (
            diffraction_detector_program_row + imaging_detector_program_row
        ) + [1]
        diffraction_detector_pos_row = [
            35.0,
            80.0,
            125.0,
            125.18,
            125.18,
            125.18,
            125.18,
        ]
        imaging_detector_pos_row = [125.0, 80.0, 35.0, 34.82, 34.82]
        positions = nCycles * (
            diffraction_detector_pos_row + imaging_detector_pos_row
        ) + [35.0]
        completed_steps = [
            0,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            2,
            2,
            2,
            2,
            2,
            3,
            3,
            3,
            3,
            3,
            3,
            3,
            4,
            4,
            4,
            4,
            4,
            5,
            5,
            5,
            5,
            5,
            5,
            5,
            6,
            7,
            7,
            7,
        ]

        assert self.child.handled_requests.mock_calls == [
            call.post(
                "writeProfile", csPort="CS1", timeArray=[0.002], userPrograms=[8]
            ),
            call.post("executeProfile"),
            call.post("moveCS1", moveTime=0.0026832816, a=34.82),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post(
                "writeProfile",
                csPort="CS1",
                timeArray=pytest.approx(times),
                velocityMode=pytest.approx(velocity_modes),
                userPrograms=pytest.approx(user_programs),
                a=pytest.approx(positions),
            ),
        ]
        assert self.o.completed_steps_lookup == completed_steps

    def test_configure_with_exposure_time_less_than_min_turnaround(self):
        self.o.imaging_angle = 50.0
        self.o.diffraction_angle = 90.0
        self.set_motor_attributes(x_pos=50.0, x_velocity=800.0, x_acceleration=100000.0)
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 0.0001
        diffraction_exposure_time = 0.3
        detectors = self._get_detector_table(
            imaging_exposure_time, diffraction_exposure_time
        )
        # Update generator duration based on validate method
        infos = self.o.on_validate(generator, {}, detectors)
        generator.duration = infos.value.duration
        generator.prepare()

        # Run configure
        self.o.on_configure(self.context, 0, nCycles, {}, generator, detectors, [])

        # Expected generator duration is affected by min turnaround time
        assert generator.duration == pytest.approx(
            self.move_time * 2 + MIN_TIME + diffraction_exposure_time
        )

        # Build up our expected values
        diffraction_detector_time_row = [2000, 250000, 250000, 2000, 300000]
        imaging_detector_time_row = [2000, 250000, 250000]
        times = nCycles * (
            diffraction_detector_time_row + imaging_detector_time_row
        ) + [2000]
        diffraction_velocity_row = [1, 0, 1, 1, 1]
        imaging_velocity_row = [1, 0, 1]
        velocity_modes = nCycles * (diffraction_velocity_row + imaging_velocity_row) + [
            3
        ]
        diffraction_detector_program_row = [1, 4, 2, 8, 8]
        imaging_detector_program_row = [1, 4, 2]
        user_programs = nCycles * (
            diffraction_detector_program_row + imaging_detector_program_row
        ) + [1]
        diffraction_detector_pos_row = [50.0, 70.0, 90.0, 90.08, 90.08]
        imaging_detector_pos_row = [90.0, 70.0, 50.0]
        positions = nCycles * (
            diffraction_detector_pos_row + imaging_detector_pos_row
        ) + [50.0]
        completed_steps = [0, 0, 1, 1, 1, 1, 1, 2, 3]

        assert self.child.handled_requests.mock_calls == [
            call.post(
                "writeProfile", csPort="CS1", timeArray=[0.002], userPrograms=[8]
            ),
            call.post("executeProfile"),
            call.post("moveCS1", moveTime=0.0017888544, a=49.92),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post(
                "writeProfile",
                csPort="CS1",
                timeArray=pytest.approx(times),
                velocityMode=pytest.approx(velocity_modes),
                userPrograms=pytest.approx(user_programs),
                a=pytest.approx(positions),
            ),
        ]
        assert self.o.completed_steps_lookup == completed_steps

    def test_configure_raises_ValueError_with_invalid_frames_per_step(self):
        self.set_motor_attributes()
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        generator.prepare()
        imaging_exposure_time = 0.01
        diffraction_exposure_time = 1.0
        detectors_with_bad_imaging_frames_per_step = DetectorTable(
            [True, True, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [3, 1, 2],
        )
        detectors_with_bad_diffraction_frames_per_step = DetectorTable(
            [True, True, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [1, 10, 2],
        )
        self.assertRaises(
            ValueError,
            self.o.on_configure,
            self.context,
            0,
            nCycles,
            {},
            generator,
            detectors_with_bad_imaging_frames_per_step,
            [],
        )
        self.assertRaises(
            ValueError,
            self.o.on_configure,
            self.context,
            0,
            nCycles,
            {},
            generator,
            detectors_with_bad_diffraction_frames_per_step,
            [],
        )

    def test_configure_raises_ValueError_when_detector_not_enabled(self):
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 0.1
        diffraction_exposure_time = 0.3
        detectors_with_imaging_disabled = DetectorTable(
            [False, True, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [1, 1, 2],
        )

        detectors_with_diffraction_disabled = DetectorTable(
            [True, False, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [1, 1, 2],
        )

        self.assertRaises(
            ValueError,
            self.o.on_configure,
            self.context,
            0,
            nCycles,
            {},
            generator,
            detectors_with_imaging_disabled,
            [],
        )
        self.assertRaises(
            ValueError,
            self.o.on_configure,
            self.context,
            0,
            nCycles,
            {},
            generator,
            detectors_with_diffraction_disabled,
            [],
        )

    def test_configure_raises_ValueError_when_exposure_is_zero(self):
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        imaging_exposure_time = 0.1
        diffraction_exposure_time = 0.3
        detectors_with_imaging_zero_exposure = DetectorTable(
            [False, True, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, 0.0, 0.0],
            [1, 1, 2],
        )

        detectors_with_diffraction_zero_exposure = DetectorTable(
            [True, False, True],
            ["imagingDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [0.0, diffraction_exposure_time, 0.0],
            [1, 1, 2],
        )

        self.assertRaises(
            ValueError,
            self.o.on_configure,
            self.context,
            0,
            nCycles,
            {},
            generator,
            detectors_with_imaging_zero_exposure,
            [],
        )
        self.assertRaises(
            ValueError,
            self.o.on_configure,
            self.context,
            0,
            nCycles,
            {},
            generator,
            detectors_with_diffraction_zero_exposure,
            [],
        )

    def test_configure_raises_ValueError_with_missing_detector(self):
        self.set_motor_attributes()
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        generator.prepare()
        exposure_time = 0.01
        detectors_without_diffraction = DetectorTable(
            [True, True],
            ["imagingDetector", "PandA"],
            ["ML-IMAGING-01", "ML-PANDA-01"],
            [exposure_time, 0.0],
            [1, 2],
        )
        detectors_without_imaging = DetectorTable(
            [True, True],
            ["diffDetector", "PandA"],
            ["ML-DIFF-01", "ML-PANDA-01"],
            [exposure_time, 0.0],
            [1, 2],
        )

        self.assertRaises(
            ValueError,
            self.o.on_configure,
            self.context,
            0,
            nCycles,
            {},
            generator,
            detectors_without_diffraction,
            [],
        )
        self.assertRaises(
            ValueError,
            self.o.on_configure,
            self.context,
            0,
            nCycles,
            {},
            generator,
            detectors_without_imaging,
            [],
        )

    def test_invalid_parameters_raise_ValueError(self):
        # Some valid parameters
        name = "beamSelectorPart"
        mri = "PMAC"
        selector_axis = "x"
        imaging_angle = 30.0
        diffraction_angle = 65.0
        imaging_detector = "imagingDetector"
        diffraction_detector = "diffDetector"
        move_time = 0.25

        # Check the valid parameters
        BeamSelectorPart(
            name,
            mri,
            selector_axis,
            imaging_angle,
            diffraction_angle,
            imaging_detector,
            diffraction_detector,
            move_time,
        )

        # Mix with one of these invalid parameters
        invalid_selector_axes = [0.0, 1]
        invalid_angles = ["not_an_angle"]
        invalid_detector_names = [10, 53.3]
        invalid_move_times = ["this is not a number", -1.0, 0.0, "-0.45"]

        # Now we check they raise errors
        for invalid_axis in invalid_selector_axes:
            self.assertRaises(
                ValueError,
                BeamSelectorPart,
                name,
                mri,
                invalid_axis,
                imaging_angle,
                diffraction_angle,
                imaging_detector,
                diffraction_detector,
                move_time,
            )

        for invalid_angle in invalid_angles:
            self.assertRaises(
                ValueError,
                BeamSelectorPart,
                name,
                mri,
                selector_axis,
                invalid_angle,
                diffraction_angle,
                imaging_detector,
                diffraction_detector,
                move_time,
            )
            self.assertRaises(
                ValueError,
                BeamSelectorPart,
                name,
                mri,
                selector_axis,
                imaging_angle,
                invalid_angle,
                imaging_detector,
                diffraction_detector,
                move_time,
            )

        for invalid_detector_name in invalid_detector_names:
            self.assertRaises(
                ValueError,
                BeamSelectorPart,
                name,
                mri,
                selector_axis,
                imaging_angle,
                diffraction_angle,
                invalid_detector_name,
                diffraction_detector,
                move_time,
            )
            self.assertRaises(
                ValueError,
                BeamSelectorPart,
                name,
                mri,
                selector_axis,
                imaging_angle,
                diffraction_angle,
                imaging_detector,
                invalid_detector_name,
                move_time,
            )

        for invalid_move_time in invalid_move_times:
            self.assertRaises(
                ValueError,
                BeamSelectorPart,
                name,
                mri,
                selector_axis,
                imaging_angle,
                diffraction_angle,
                imaging_detector,
                diffraction_detector,
                invalid_move_time,
            )
