from typing import Tuple

from annotypes import Anno, add_call_types
from scanpointgenerator import CompoundGenerator, LineGenerator, StaticPointGenerator

from malcolm.modules import builtin, scanning
from malcolm.modules.scanning.util import ADetectorTable

from ..util import AlternatingDelayAfterMutator, get_min_turnaround_and_interval
from .pmacchildpart import PmacChildPart, VelocityModes

# 80 char line lengths...
AIV = builtin.parts.AInitialVisibility

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri
with Anno("Name of the selector axis scannable"):
    ASelectorAxis = str
with Anno("Angle of for the tomography detector position"):
    ATomoAngle = float
with Anno("Angle of the diffraction detector position"):
    ADiffAngle = float
with Anno("Name of the tomography detector (should match DetectorChildPart)"):
    ATomoDetector = str
with Anno("Name of the diffraction detector (should match DetectorChildPart)"):
    ADiffDetector = str
with Anno("Minimum move time between the two positions"):
    AMoveTime = float


class BeamSelectorPart(PmacChildPart):
    def __init__(
        self,
        name: APartName,
        mri: AMri,
        selector_axis: ASelectorAxis,
        tomo_angle: ATomoAngle,
        diff_angle: ADiffAngle,
        tomo_detector: ATomoDetector,
        diff_detector: ADiffDetector,
        move_time: AMoveTime,
        initial_visibility: AIV = False,
    ) -> None:
        # Some basic checking
        parsed_move_time = float(move_time)
        if parsed_move_time <= 0.0:
            raise ValueError("Move time must be larger than zero.")
        elif not isinstance(selector_axis, str):
            raise ValueError("Selector axis name must be a string")
        elif not isinstance(tomo_detector, str):
            raise ValueError("Tomography detector name must be a string")
        elif not isinstance(diff_detector, str):
            raise ValueError("Diffraction detector name must be a string")

        super().__init__(name, mri, initial_visibility)
        self.selector_axis = selector_axis
        self.tomo_detector = tomo_detector
        self.diff_detector = diff_detector
        self.tomo_angle = float(tomo_angle)
        self.diff_angle = float(diff_angle)
        self.move_time = float(move_time)

    def _get_detector_exposure_times(
        self, detectors: ADetectorTable
    ) -> Tuple[float, float]:
        assert detectors, "No detector table found"
        diff_detector_found = False
        tomo_detector_found = False
        diff_detector_exposure = 0.0
        tomo_detector_exposure = 0.0
        for enable, name, mri, exposure, frames in detectors.rows():
            if name == self.diff_detector and enable:
                assert frames == 1, "%s (mri %s) can only do 1 frame per step" % (
                    name,
                    mri,
                )
                diff_detector_exposure = exposure
                diff_detector_found = True
            elif name == self.tomo_detector and enable:
                assert frames == 1, "%s (mri %s) can only do 1 frame per step" % (
                    name,
                    mri,
                )
                tomo_detector_exposure = exposure
                tomo_detector_found = True
            if diff_detector_found and tomo_detector_found:
                break
        if not diff_detector_found:
            raise ValueError("Diffraction detector not found in table")
        elif not tomo_detector_found:
            raise ValueError("Tomography detector not found in table")

        return diff_detector_exposure, tomo_detector_exposure

    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        part_info: scanning.hooks.APartInfo,
        generator: scanning.hooks.AGenerator,
        detectors: ADetectorTable,
        axesToMove: scanning.hooks.AAxesToMove,
    ) -> None:

        # Find out the exposure times of our detectors
        (
            diff_detector_exposure,
            tomo_detector_exposure,
        ) = self._get_detector_exposure_times(detectors)

        # Increase the time at each position to the minimum turnaround if necessary
        min_turnaround = get_min_turnaround_and_interval(part_info)[0]
        time_at_diff_position = max(min_turnaround, diff_detector_exposure)
        time_at_tomo_position = max(min_turnaround, tomo_detector_exposure)

        # Build our mutator
        mutator = AlternatingDelayAfterMutator(
            time_at_diff_position, time_at_tomo_position
        )

        # Double the number of points to get rotations (2 points per cycle)
        static_axis = generator.generators[0]
        assert isinstance(
            static_axis, StaticPointGenerator
        ), "Static Point Generator not configured correctly"
        static_axis = StaticPointGenerator(size=static_axis.size * 2)
        steps_to_do *= 2

        # Create a linear scan axis (proper rotation)
        selector_axis = LineGenerator(
            self.selector_axis,
            "deg",
            self.tomo_angle,
            self.diff_angle,
            1,
            alternate=True,
        )
        axesToMove = [self.selector_axis]

        # Build the compound generator for the PMAC
        new_generator = CompoundGenerator(
            [static_axis, selector_axis],
            [],
            [mutator],
            duration=self.move_time,
            continuous=True,
        )
        new_generator.prepare()

        # Main generator duration should be time for complete cycle
        generator.duration = (
            2 * self.move_time + time_at_diff_position + time_at_tomo_position
        )

        super().on_configure(
            context, completed_steps, steps_to_do, part_info, new_generator, axesToMove
        )

    def add_tail_off(self):
        # The current point
        current_point = self.generator.get_point(self.steps_up_to - 1)
        # the next point is same as the previous
        next_point = self.generator.get_point(self.steps_up_to - 2)

        # insert the turnaround points
        self.insert_gap(current_point, next_point, self.steps_up_to + 1)

        # Do the last move
        #        user_program = self.get_user_program(PointType.TURNAROUND)
        #        self.add_profile_point(tail_off_time, ZERO_VELOCITY,
        #                               user_program,
        #                               self.steps_up_to, axis_points)
        # Mangle the last point to end the scan
        self.profile["velocityMode"][-1] = VelocityModes.ZERO_VELOCITY
        # user_program = self.get_user_program(PointType.TURNAROUND)
        # self.profile["userProgram"][-1] = user_program

        self.end_index = self.steps_up_to
