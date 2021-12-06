from typing import Optional, Tuple

from annotypes import Anno, add_call_types
from scanpointgenerator import (
    CompoundGenerator,
    Generator,
    LineGenerator,
    StaticPointGenerator,
)

from malcolm.modules import builtin, scanning
from malcolm.modules.scanning.util import ADetectorTable

from ..util import AlternatingDelayAfterMutator, get_min_turnaround
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
with Anno("Minimum move time between the two positions in seconds"):
    AMoveTime = float


class BeamSelectorPart(PmacChildPart):
    """
    This part is for the K11 beam selector scan.

    It moves a motor between two positions, holding at each position for the exposure
    time of a particular detector before moving.
    """

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        selector_axis: ASelectorAxis,
        imaging_angle: ATomoAngle,
        diffraction_angle: ADiffAngle,
        imaging_detector: ATomoDetector,
        diffraction_detector: ADiffDetector,
        move_time: AMoveTime,
        initial_visibility: AIV = False,
    ) -> None:
        # Some basic checking
        parsed_move_time = float(move_time)
        if parsed_move_time <= 0.0:
            raise ValueError("Move time must be larger than zero.")
        elif not isinstance(selector_axis, str):
            raise ValueError("Selector axis name must be a string")
        elif not isinstance(imaging_detector, str):
            raise ValueError("Tomography detector name must be a string")
        elif not isinstance(diffraction_detector, str):
            raise ValueError("Diffraction detector name must be a string")

        super().__init__(name, mri, initial_visibility)
        self.selector_axis = selector_axis
        self.imaging_detector = imaging_detector
        self.diffraction_detector = diffraction_detector
        self.imaging_angle = float(imaging_angle)
        self.diffraction_angle = float(diffraction_angle)
        self.move_time = parsed_move_time

    def _get_error_message(self, name: str, mri: str, message: str) -> str:
        return f"{mri} (name {name}): {message}"

    def _check_detector_parameters(
        self, name: str, mri: str, frames: int, enable: bool, exposure: float
    ) -> None:
        if frames != 1:
            raise ValueError(
                self._get_error_message(name, mri, "Can only do 1 frame per step")
            )
        elif not enable:
            raise ValueError(
                self._get_error_message(name, mri, "Detector needs to be enabled")
            )
        elif exposure <= 0.0:
            raise ValueError(
                self._get_error_message(
                    name, mri, "Exposure needs to be greater than zero"
                )
            )

    def _get_detector_exposure_times(
        self, detectors: ADetectorTable
    ) -> Tuple[float, float]:
        assert detectors, "No detector table found"
        diffraction_detector_found = False
        imaging_detector_found = False
        diffraction_detector_exposure = 0.0
        imaging_detector_exposure = 0.0
        for enable, name, mri, exposure, frames in detectors.rows():
            if name == self.diffraction_detector:
                self._check_detector_parameters(name, mri, frames, enable, exposure)
                diffraction_detector_exposure = exposure
                diffraction_detector_found = True
            elif name == self.imaging_detector:
                self._check_detector_parameters(name, mri, frames, enable, exposure)
                imaging_detector_exposure = exposure
                imaging_detector_found = True
            if diffraction_detector_found and imaging_detector_found:
                break
        if not diffraction_detector_found:
            raise ValueError("Diffraction detector not found in table")
        elif not imaging_detector_found:
            raise ValueError("Tomography detector not found in table")

        return diffraction_detector_exposure, imaging_detector_exposure

    def _get_time_at_positions(
        self, part_info: scanning.hooks.APartInfo, detectors: ADetectorTable
    ) -> Tuple[float, float]:
        # Find out the exposure times of our detectors
        (
            diffraction_detector_exposure,
            imaging_detector_exposure,
        ) = self._get_detector_exposure_times(detectors)

        # Increase the time at each position to the minimum turnaround if necessary
        min_turnaround = get_min_turnaround(part_info)
        time_at_diffraction_position = max(
            min_turnaround.time, diffraction_detector_exposure
        )
        time_at_imaging_position = max(min_turnaround.time, imaging_detector_exposure)

        return time_at_diffraction_position, time_at_imaging_position

    def _calculate_cycle_duration(
        self, time_at_diffraction_position: float, time_at_imaging_position: float
    ) -> float:
        return (
            time_at_diffraction_position + time_at_imaging_position + 2 * self.move_time
        )

    def _check_generator_is_static(self, primary_generator: Generator) -> None:
        assert isinstance(
            primary_generator, StaticPointGenerator
        ), f"Expected primary generator to be static, got {type(primary_generator)}"

    @add_call_types
    def on_validate(
        self,
        generator: scanning.hooks.AGenerator,
        part_info: scanning.hooks.APartInfo,
        detectors: ADetectorTable,
    ) -> Optional[scanning.hooks.UParameterTweakInfos]:
        # Check the primary generator is static
        self._check_generator_is_static(generator.generators[0])

        # Calculate the time that should be spent at each position
        (
            time_at_diffraction_position,
            time_at_imaging_position,
        ) = self._get_time_at_positions(part_info, detectors)
        # Now calculate how long one cycle should take
        cycle_duration = self._calculate_cycle_duration(
            time_at_diffraction_position, time_at_imaging_position
        )
        # See if we need to tweak the generator
        if generator.duration != cycle_duration:
            # Return the generator with our cycle duration
            self.log.debug(
                f"{self.name}: tweaking generator duration from {generator.duration} "
                f"to {cycle_duration}"
            )
            serialized = generator.to_dict()
            new_generator = CompoundGenerator.from_dict(serialized)
            new_generator.duration = cycle_duration
            return scanning.infos.ParameterTweakInfo("generator", new_generator)
        else:
            return None

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
        # Check the provided generator is formatted as expected
        static_axis = generator.generators[0]
        self._check_generator_is_static(static_axis)

        # Calculate the time that should be spent at each position
        (
            time_at_diffraction_position,
            time_at_imaging_position,
        ) = self._get_time_at_positions(part_info, detectors)

        # Check that the duration matches the expected output from Validate
        expected_duration = self._calculate_cycle_duration(
            time_at_diffraction_position, time_at_imaging_position
        )
        assert (
            generator.duration == expected_duration
        ), f"Expected a duration of {expected_duration}, got {generator.duration}"

        # Build our mutator
        mutator = AlternatingDelayAfterMutator(
            time_at_diffraction_position, time_at_imaging_position
        )

        # Double the number of points so we have 2 points per complete cycle
        static_axis = StaticPointGenerator(size=static_axis.size * 2)
        steps_to_do *= 2

        # Create a linear scan axis to handle motion between the positions
        selector_axis = LineGenerator(
            self.selector_axis,
            "deg",
            self.imaging_angle,
            self.diffraction_angle,
            1,
            alternate=True,
        )
        axesToMove = [self.selector_axis]

        # Build the compound generator for the PMAC for handling the motion.
        # We build this in configure because the duration may cause some issues
        # when trying to validate the detectors taking part due to comparing it
        # to their exposure times - which is not relevant for this scan as the
        # exposures will be during the delay_after phase at each position.
        new_generator = CompoundGenerator(
            [static_axis, selector_axis],
            [],
            [mutator],
            duration=self.move_time,
            continuous=True,
        )
        new_generator.prepare()

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

        # Set the velocity of the last point to 0
        self.profile["velocityMode"][-1] = VelocityModes.ZERO_VELOCITY

        self.end_index = self.steps_up_to
