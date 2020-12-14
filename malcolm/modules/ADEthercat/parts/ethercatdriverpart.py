from typing import Any

from annotypes import add_call_types

from malcolm.core import Context, PartRegistrar
from malcolm.modules import ADCore, builtin, scanning
from malcolm.modules.scanning.hooks import AContext, PostRunReadyHook, PreRunHook

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


@builtin.util.no_save("numberOfSamples", "triggerMode")
class EthercatDriverPart(ADCore.parts.DetectorDriverPart):
    def __init__(self, name: APartName, mri: AMri) -> None:
        super().__init__(name, mri, soft_trigger_modes="Internal")

    def setup_detector(
        self,
        context: Context,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        duration: float,
        part_info: scanning.hooks.APartInfo,
        **kwargs: Any,
    ) -> None:

        super().setup_detector(
            context, completed_steps, steps_to_do, duration, part_info, **kwargs
        )

        # We want to have the driver just run in continuous mode using software trigger
        child = context.block_view(self.mri)
        child.imageMode.put_value("Continuous")
        child.triggerMode.put_value("Internal")
        child.numberOfSamples.put_value(1000)
        child.put_attribute_values(kwargs)

    @add_call_types
    def start_acquisition(self, context: AContext) -> None:
        self.arm_detector(context)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Arm in PreRun so we don't get too much pre-scan data
        registrar.hook(PreRunHook, self.start_acquisition)
        registrar.hook(PostRunReadyHook, self.on_abort)

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        # We override run as we arm in PreRun and do not want to
        # wait for a specific number of frames due to triggers
        # not being synchronised with the ethercat frames.
        pass
