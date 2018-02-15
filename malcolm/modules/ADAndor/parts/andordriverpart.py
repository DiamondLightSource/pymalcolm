from annotypes import add_call_types, Any

from malcolm.modules import ADCore, scanning


class AndorDriverPart(ADCore.parts.DetectorDriverPart):
    """Part for using andor_driver_block in a scan"""
    def __init__(self,
                 name,  # type: ADCore.parts.APartName
                 mri,  # type: ADCore.parts.AMri
                 ):
        # type: (...) -> None
        super(AndorDriverPart, self).__init__(name, mri)

    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  generator,  # type: scanning.hooks.AGenerator
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> None
        self.actions.setup_detector(
            context, completed_steps, steps_to_do, imageMode="Fixed",
            exposure=generator.duration - 13e-3, **kwargs)
        # Need to reset acquirePeriod as it's sometimes wrong
        child = context.block_view(self.mri)
        child.acquirePeriod.put_value(generator.duration)
        # Start now if we are hardware triggered
        # self.is_hardware_triggered = child.triggerMode == "Hardware"
        if self.is_hardware_triggered:
            self.actions.arm_detector(context)
