from typing import Any

import cothread
from annotypes import Anno, add_call_types

from malcolm.modules import ADCore, builtin, scanning

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri

with Anno("Directory to write data to"):
    AFileDir = str


class TucsenDriverPart(ADCore.parts.DetectorDriverPart):
    def __init__(self, name, mri):
        # type: (APartName, AMri) -> None
        super(TucsenDriverPart, self).__init__(
            name, mri, soft_trigger_modes=["Internal", "Software"]
        )

    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        part_info: scanning.hooks.APartInfo,
        generator: scanning.hooks.AGenerator,
        fileDir: scanning.hooks.AFileDir,
        **kwargs: Any,
    ) -> None:
        super(TucsenDriverPart, self).on_configure(
            context,
            completed_steps,
            steps_to_do,
            part_info,
            generator,
            fileDir,
            **kwargs,
        )
        cothread.Sleep(1.5)
