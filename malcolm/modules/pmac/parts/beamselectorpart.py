from malcolm.core import Future, Block, PartRegistrar, Put, Request
from malcolm.modules import builtin, scanning
from malcolm.modules.pmac.parts import PmacChildPart
from malcolm.modules.pmac.util import get_motion_trigger
from scanpointgenerator import LineGenerator, CompoundGenerator, \
    StaticPointGenerator

from malcolm.modules.scanning.infos import MinTurnaroundInfo
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

        static_axis = generator.generators[0]
        assert isinstance(static_axis, StaticPointGenerator), "Bad"
        selectorAxis = LineGenerator("x", "mm", 0.0, 0.5, 1,
                                     alternate=True)
        newGenerator = CompoundGenerator([static_axis, selectorAxis],
                                         [],
                                         [], generator.duration,
                                         continuous=False)
        newGenerator.prepare()

        t_min = 0.1
        part_info[""] = [MinTurnaroundInfo(
            (generator.duration - t_min) / 2)]

        super(BeamSelectorPart, self).configure(context,
                                                completed_steps,
                                                steps_to_do,
                                                part_info,
                                                newGenerator,
                                                axesToMove)
