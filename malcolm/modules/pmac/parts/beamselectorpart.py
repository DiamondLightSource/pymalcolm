from malcolm.core import Future, Block, PartRegistrar, Put, Request
from malcolm.modules import builtin, scanning
from malcolm.modules.pmac.parts import PmacChildPart
from malcolm.modules.pmac.util import get_motion_trigger
from scanpointgenerator import LineGenerator, CompoundGenerator

from ..util import cs_axis_mapping, points_joined, point_velocities, MIN_TIME, \
    profile_between_points, cs_port_with_motors_in, get_motion_axes

from annotypes import add_call_types, TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Dict, List

# 80 char line lengths...
AIV = builtin.parts.AInitialVisibility

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri

##############################
# Globals from pmac child part
##############################
# Number of seconds that a trajectory tick is
TICK_S = 0.000001

# Longest move time we can request
MAX_MOVE_TIME = 4.0

# velocity modes
PREV_TO_NEXT = 0
PREV_TO_CURRENT = 1
CURRENT_TO_NEXT = 2
ZERO_VELOCITY = 3

# user programs
NO_PROGRAM = 0  # Do nothing
LIVE_PROGRAM = 1  # GPIO123 = 1, 0, 0
DEAD_PROGRAM = 2  # GPIO123 = 0, 1, 0
MID_PROGRAM = 4  # GPIO123 = 0, 0, 1
ZERO_PROGRAM = 8  # GPIO123 = 0, 0, 0

class BeamSelectorPart(PmacChildPart):

    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 initial_visibility=None  # type: AIV
                 ):
        # type: (...) -> None
        super(BeamSelectorPart, self).__init__(name, mri, initial_visibility)

    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  axesToMove,  # type: scanning.hooks.AAxesToMove
                  ):  # type: (...) -> None

        context.unsubscribe_all()
        child = context.block_view(self.mri)

        # Store what sort of triggers we need to output
        self.output_triggers = get_motion_trigger(part_info)

        # Check if we should be taking part in the scan
        motion_axes = get_motion_axes(generator, axesToMove)
        assert motion_axes == ['y'] # todo change this to verChopper

        need_gpio = self.output_triggers != scanning.infos.MotionTrigger.NONE
        if motion_axes or need_gpio:
            # Taking part, so store generator
            # Recreate the beam selector axis
            staticAxis = generator.generators[0]
            selectorAxis = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
            newGenerator = CompoundGenerator([staticAxis, selectorAxis], [],[], generator.duration)
            assert newGenerator.axes == ['y', 'x']
            newGenerator.prepare()
            self.generator = newGenerator

            motion_axes = ["x", "y"]
            steps_to_do *= 2 # since we added another axis

        else:
            # Flag as not taking part
            self.generator = None
            return

        # See if there is a minimum turnaround
        infos = scanning.infos.MinTurnaroundInfo.filter_values(part_info)
        if infos:
            assert len(infos) == 1, \
                "Expected 0 or 1 MinTurnaroundInfos, got %d" % len(infos)
            self.min_turnaround = max(MIN_TIME, infos[0].gap)
        else:
            self.min_turnaround = MIN_TIME

        # Work out the cs_port we should be using
        layout_table = child.layout.value
        if motion_axes:
            self.axis_mapping = cs_axis_mapping(
                context, layout_table, motion_axes)
            # Check units for everything in the axis mapping
            # TODO: reinstate this when GDA does it properly
            # for axis_name, motor_info in sorted(self.axis_mapping.items()):
            #     assert motor_info.units == generator.units[axis_name], \
            #         "%s: Expected scan units of %r, got %r" % (
            #         axis_name, motor_info.units, generator.units[axis_name])
            # Guaranteed to have an entry in axis_mapping otherwise
            # cs_axis_mapping would fail, so pick its cs_port
            cs_port = list(self.axis_mapping.values())[0].cs_port
        else:
            # No axes to move, but if told to output triggers we still need to
            # do something
            self.axis_mapping = {}
            # Pick the first cs we find that has an axis assigned
            cs_port = cs_port_with_motors_in(context, layout_table)

        # Reset GPIOs
        # TODO: we might need to put this in pause if the PandA logic doesn't
        # copy with a trigger staying high
        child.writeProfile(csPort=cs_port, timeArray=[MIN_TIME],
                           userPrograms=[ZERO_PROGRAM])
        child.executeProfile()

        if motion_axes:
            # Start off the move to the start
            fs = self.move_to_start(child, cs_port, completed_steps)
        else:
            fs = []

        # Set how far we should be going and the completed steps lookup
        self.steps_up_to = completed_steps + steps_to_do
        self.completed_steps_lookup = []
        # Reset the profiles that still need to be sent
        self.profile = dict(
            timeArray=[],
            velocityMode=[],
            userPrograms=[],
        )
        self.time_since_last_pvt = 0

        for info in self.axis_mapping.values():
            self.profile[info.cs_axis.lower()] = []
        self.calculate_generator_profile(completed_steps, do_run_up=True)
        self.write_profile_points(child, cs_port)
        # Wait for the motors to have got to the start
        context.wait_all_futures(fs)