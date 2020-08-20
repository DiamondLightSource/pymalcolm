from malcolm.core import Context
from malcolm.modules import scanning
from malcolm.modules.ADCore.parts import DetectorDriverPart


class OdinDriverPart(DetectorDriverPart):
        def setup_detector(self,
                       context,  # type: Context
                       completed_steps,  # type: scanning.hooks.ACompletedSteps
                       steps_to_do,  # type: scanning.hooks.AStepsToDo
                       duration,  # type: float
                       part_info,  # type: scanning.hooks.APartInfo
                       **kwargs  # type: Any
                       ):
        # type: (...) -> None
        super(OdinDriverPart, self).setup_detector(context, 0, steps_to_do, duration, part_info)
