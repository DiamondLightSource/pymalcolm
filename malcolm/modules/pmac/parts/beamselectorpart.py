from malcolm.modules import builtin, scanning
from malcolm.modules.pmac.parts import PmacChildPart
from scanpointgenerator import LineGenerator, CompoundGenerator, \
    StaticPointGenerator
from malcolm.modules.scanning.infos import MinTurnaroundInfo
from ..util import MIN_INTERVAL, MIN_TIME

from annotypes import add_call_types, TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Dict, List

# 80 char line lengths...
AIV = builtin.parts.AInitialVisibility

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri
AAxisName = builtin.parts.AValue
AAngle = builtin.parts.AValue

class BeamSelectorPart(PmacChildPart):

    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 selectorAxis, # type: AAxisName
                 startAngle, # type: AAngle
                 endAngle, # type: AAngle
                 initial_visibility=None  # type: AIV
                 ):
        # type: (...) -> None
        super(BeamSelectorPart, self).__init__(name, mri, initial_visibility)
        self.selectorAxis = selectorAxis

        try:
            self.startAngle = float(startAngle)
            self.endAngle = float(endAngle)
        except:
            self.startAngle = 0.0
            self.endAngle = 0.0

        self.t_move = float(0.500)

    @add_call_types
    def on_configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  axesToMove,  # type: scanning.hooks.AAxesToMove
                  ):  # type: (...) -> None

        static_axis = generator.generators[0]
        assert isinstance(static_axis, StaticPointGenerator), \
            "Static Point Generator not configured correctly"
        selector_axis = LineGenerator(self.selectorAxis,
                                      "deg",
                                      self.startAngle,
                                      self.endAngle,
                                      1,
                                      alternate=True)
        axesToMove = [self.selectorAxis]

        def get_minturnaround():
            # See if there is a minimum turnaround
            infos = scanning.infos.MinTurnaroundInfo.filter_values(
                part_info)
            if infos:
                assert len(infos) == 1, \
                    "Expected 0 or 1 MinTurnaroundInfos, got %d" % len(
                        infos)
                min_turnaround = max(MIN_TIME, infos[0].gap)
                min_interval = infos[0].interval
            else:
                min_turnaround = MIN_TIME
                min_interval = MIN_INTERVAL

            return min_turnaround, min_interval

        min_turnaround = get_minturnaround()[0]
        exposure_time = generator.duration - self.t_move
        if exposure_time < min_turnaround:
            exposure_time = min_turnaround

        new_generator = \
            CompoundGenerator([static_axis, selector_axis],
                              [],
                              [],
                              duration=self.t_move,
                              continuous=True,
                              delay_after=exposure_time)
        new_generator.prepare()

        super(BeamSelectorPart, self).on_configure(context,
                                                completed_steps,
                                                steps_to_do,
                                                part_info,
                                                new_generator,
                                                axesToMove)
