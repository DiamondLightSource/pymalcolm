import shutil

import pytest
from mock import call
from scanpointgenerator import CompoundGenerator, StaticPointGenerator

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
            tomo_angle=0,
            diff_angle=0.5,
            tomo_detector="tomoDetector",
            diff_detector="diffDetector",
            move_time=self.move_time,
        )
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

        pass

    def tearDown(self):
        del self.context
        self.process.stop(timeout=1)
        # Remove config directory
        print(["rm", "-rf", self.config_dir.value])
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
            ["tomoDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [1, 1, 2],
        )

    def test_configure_with_single_cycle(self):
        self.set_motor_attributes()
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        generator.prepare()
        imaging_exposure_time = 0.01
        diffraction_exposure_time = 1.0
        detectors = self._get_detector_table(
            imaging_exposure_time, diffraction_exposure_time
        )
        self.o.on_configure(self.context, 0, nCycles, {}, generator, detectors, [])

        # Expected generator duration is sum of exposure times + 2*move_time
        assert (
            generator.duration
            == self.move_time * 2 + imaging_exposure_time + diffraction_exposure_time
        )

        assert self.child.handled_requests.mock_calls == [
            call.post(
                "writeProfile", csPort="CS1", timeArray=[0.002], userPrograms=[8]
            ),
            call.post("executeProfile"),
            call.post("moveCS1", moveTime=0.790569415, a=-0.125),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post(
                "writeProfile",
                csPort="CS1",
                timeArray=pytest.approx(
                    [
                        250000,
                        250000,
                        250000,
                        250000,
                        500000,
                        250000,
                        250000,
                        250000,
                        250000,
                        500000,
                        250000,
                    ]
                ),
                velocityMode=pytest.approx([1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 3]),
                userPrograms=pytest.approx([1, 4, 2, 8, 8, 1, 4, 2, 8, 8, 1]),
                a=pytest.approx(
                    [0.0, 0.25, 0.5, 0.625, 0.625, 0.5, 0.25, 0.0, -0.125, -0.125, 0.0]
                ),
            ),
        ]
        assert self.o.completed_steps_lookup == [0, 0, 1, 1, 1, 1, 1, 2, 3, 3, 3]

    def test_configure_with_three_cycles(self):
        self.set_motor_attributes()
        nCycles = 3
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        generator.prepare()
        imaging_exposure_time = 0.01
        diffraction_exposure_time = 1.0
        detectors = self._get_detector_table(
            imaging_exposure_time, diffraction_exposure_time
        )
        self.o.on_configure(self.context, 0, nCycles, {}, generator, detectors, [])

        # Expected generator duration is sum of exposure times + 2*move_time
        assert (
            generator.duration
            == self.move_time * 2 + imaging_exposure_time + diffraction_exposure_time
        )

        assert self.child.handled_requests.mock_calls == [
            call.post(
                "writeProfile", csPort="CS1", timeArray=[0.002], userPrograms=[8]
            ),
            call.post("executeProfile"),
            call.post("moveCS1", moveTime=0.790569415, a=-0.125),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post(
                "writeProfile",
                csPort="CS1",
                timeArray=pytest.approx(
                    [
                        250000,
                        250000,
                        250000,
                        250000,
                        500000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        500000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        250000,
                        500000,
                        250000,
                        250000,
                        250000,
                        250000,
                        500000,
                        250000,
                    ]
                ),
                velocityMode=pytest.approx(
                    [
                        1,
                        0,
                        1,
                        1,
                        1,
                        1,
                        0,
                        1,
                        1,
                        1,
                        0,
                        1,
                        1,
                        1,
                        1,
                        0,
                        1,
                        1,
                        1,
                        0,
                        1,
                        1,
                        1,
                        1,
                        0,
                        1,
                        1,
                        1,
                        3,
                    ]
                ),
                userPrograms=pytest.approx(
                    [
                        1,
                        4,
                        2,
                        8,
                        8,
                        1,
                        4,
                        2,
                        8,
                        1,
                        4,
                        2,
                        8,
                        8,
                        1,
                        4,
                        2,
                        8,
                        1,
                        4,
                        2,
                        8,
                        8,
                        1,
                        4,
                        2,
                        8,
                        8,
                        1,
                    ]
                ),
                a=pytest.approx(
                    [
                        0.0,
                        0.25,
                        0.5,
                        0.625,
                        0.625,
                        0.5,
                        0.25,
                        0.0,
                        -0.125,
                        0.0,
                        0.25,
                        0.5,
                        0.625,
                        0.625,
                        0.5,
                        0.25,
                        0.0,
                        -0.125,
                        0.0,
                        0.25,
                        0.5,
                        0.625,
                        0.625,
                        0.5,
                        0.25,
                        0.0,
                        -0.125,
                        -0.125,
                        0.0,
                    ]
                ),
            ),
        ]
        assert self.o.completed_steps_lookup == [
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
            3,
            3,
            3,
            3,
            3,
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

    def test_configure_with_exposure_shorter_than_min_turnaround(self):
        self.set_motor_attributes()
        nCycles = 1
        generator = CompoundGenerator(
            [StaticPointGenerator(nCycles)], [], [], duration=0.0
        )
        generator.prepare()
        imaging_exposure_time = 0.0001
        diffraction_exposure_time = 1.0
        detectors = self._get_detector_table(
            imaging_exposure_time, diffraction_exposure_time
        )
        self.o.on_configure(self.context, 0, nCycles, {}, generator, detectors, [])

        # Expected generator duration is longer because of min turnaround
        assert (
            generator.duration
            == self.move_time * 2 + diffraction_exposure_time + MIN_TIME
        )

        assert self.child.handled_requests.mock_calls == [
            call.post(
                "writeProfile", csPort="CS1", timeArray=[0.002], userPrograms=[8]
            ),
            call.post("executeProfile"),
            call.post("moveCS1", moveTime=0.790569415, a=-0.125),
            # pytest.approx to allow sensible compare with numpy arrays
            call.post(
                "writeProfile",
                csPort="CS1",
                timeArray=pytest.approx(
                    [
                        250000,
                        250000,
                        250000,
                        250000,
                        500000,
                        250000,
                        250000,
                        250000,
                        250000,
                        500000,
                        250000,
                    ]
                ),
                velocityMode=pytest.approx([1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 3]),
                userPrograms=pytest.approx([1, 4, 2, 8, 8, 1, 4, 2, 8, 8, 1]),
                a=pytest.approx(
                    [0.0, 0.25, 0.5, 0.625, 0.625, 0.5, 0.25, 0.0, -0.125, -0.125, 0.0]
                ),
            ),
        ]
        assert self.o.completed_steps_lookup == [0, 0, 1, 1, 1, 1, 1, 2, 3, 3, 3]

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
            ["tomoDetector", "PandA"],
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

    def test_configure_raises_AssertionError_with_invalid_frames_per_step(self):
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
            ["tomoDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [3, 1, 2],
        )
        detectors_with_bad_diffraction_frames_per_step = DetectorTable(
            [True, True, True],
            ["tomoDetector", "diffDetector", "PandA"],
            ["ML-IMAGING-01", "ML-DIFF-01", "ML-PANDA-01"],
            [imaging_exposure_time, diffraction_exposure_time, 0.0],
            [1, 10, 2],
        )
        self.assertRaises(
            AssertionError,
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
            AssertionError,
            self.o.on_configure,
            self.context,
            0,
            nCycles,
            {},
            generator,
            detectors_with_bad_diffraction_frames_per_step,
            [],
        )

    def test_invalid_parameters_raise_ValueError(self):
        # Some valid parameters
        name = "beamSelectorPart"
        mri = "PMAC"
        selector_axis = "x"
        tomo_angle = 30.0
        diff_angle = 65.0
        tomo_detector = "tomoDetector"
        diff_detector = "diffDetector"
        move_time = 0.25

        # Check the valid parameters
        BeamSelectorPart(
            name,
            mri,
            selector_axis,
            tomo_angle,
            diff_angle,
            tomo_detector,
            diff_detector,
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
                tomo_angle,
                diff_angle,
                tomo_detector,
                diff_detector,
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
                diff_angle,
                tomo_detector,
                diff_detector,
                move_time,
            )
            self.assertRaises(
                ValueError,
                BeamSelectorPart,
                name,
                mri,
                selector_axis,
                tomo_angle,
                invalid_angle,
                tomo_detector,
                diff_detector,
                move_time,
            )

        for invalid_detector_name in invalid_detector_names:
            self.assertRaises(
                ValueError,
                BeamSelectorPart,
                name,
                mri,
                selector_axis,
                tomo_angle,
                diff_angle,
                invalid_detector_name,
                diff_detector,
                move_time,
            )
            self.assertRaises(
                ValueError,
                BeamSelectorPart,
                name,
                mri,
                selector_axis,
                tomo_angle,
                diff_angle,
                tomo_detector,
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
                tomo_angle,
                diff_angle,
                tomo_detector,
                diff_detector,
                invalid_move_time,
            )
