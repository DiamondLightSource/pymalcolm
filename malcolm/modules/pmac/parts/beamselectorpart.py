from annotypes import add_call_types
from scanpointgenerator import CompoundGenerator, LineGenerator, StaticPointGenerator

from malcolm.modules import builtin, scanning

from ..util import MIN_INTERVAL, MIN_TIME
from .pmacchildpart import PmacChildPart, VelocityModes

# 80 char line lengths...
AIV = builtin.parts.AInitialVisibility

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri
AAxisName = builtin.parts.AValue
AAngle = builtin.parts.AValue
ATime = builtin.parts.AValue


class BeamSelectorPart(PmacChildPart):
    def __init__(
        self,
        name: APartName,
        mri: AMri,
        selectorAxis: AAxisName,
        tomoAngle: AAngle,
        diffAngle: AAngle,
        moveTime: ATime,
        initial_visibility: AIV = False,
    ) -> None:
        super().__init__(name, mri, initial_visibility)
        self.selectorAxis = selectorAxis

        try:
            self.tomoAngle = float(tomoAngle)
            self.diffAngle = float(diffAngle)
            self.move_time = float(moveTime)
        except ValueError:
            self.tomoAngle = 0.0
            self.diffAngle = 0.0
            self.move_time = 0.500  # seconds

    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        part_info: scanning.hooks.APartInfo,
        generator: scanning.hooks.AGenerator,
        axesToMove: scanning.hooks.AAxesToMove,
    ) -> None:

        # Double the number of cycles to get rotations
        static_axis = generator.generators[0]
        assert isinstance(
            static_axis, StaticPointGenerator
        ), "Static Point Generator not configured correctly"
        static_axis = StaticPointGenerator(size=static_axis.size * 2)
        steps_to_do *= 2

        # Create a linear scan axis (proper rotation)
        selector_axis = LineGenerator(
            self.selectorAxis, "deg", self.tomoAngle, self.diffAngle, 1, alternate=True
        )
        axesToMove = [self.selectorAxis]

        def get_minturnaround():
            # See if there is a minimum turnaround
            infos = scanning.infos.MinTurnaroundInfo.filter_values(part_info)
            if infos:
                assert (
                    len(infos) == 1
                ), "Expected 0 or 1 MinTurnaroundInfos, got %d" % len(infos)
                min_turnaround = max(MIN_TIME, infos[0].gap)
                min_interval = infos[0].interval
            else:
                min_turnaround = MIN_TIME
                min_interval = MIN_INTERVAL

            return min_turnaround, min_interval

        # Calculate the exposure time
        min_turnaround = get_minturnaround()[0]
        cycle_duration = generator.duration
        exposure_time = cycle_duration / 2 - self.move_time
        if exposure_time < min_turnaround:
            exposure_time = min_turnaround

        new_generator = CompoundGenerator(
            [static_axis, selector_axis],
            [],
            [],
            duration=self.move_time,
            continuous=True,
            delay_after=exposure_time,
        )
        new_generator.prepare()

        # Reduce the exposure of the camera/detector
        generator.duration = exposure_time

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
