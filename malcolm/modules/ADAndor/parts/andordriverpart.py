from annotypes import add_call_types, Any

from malcolm.modules import ADCore, scanning


class AndorDriverPart(ADCore.parts.DetectorDriverPart):
    """Part for using andor_driver_block in a scan"""
    def __init__(self,
                 name,  # type: ADCore.parts.APartName
                 mri,  # type: ADCore.parts.AMri
                 ):
        # type: (...) -> None
        super(AndorDriverPart, self).__init__(
            name, mri, initial_readout_time=13e-3)

    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  generator,  # type: scanning.hooks.AGenerator
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> None
        # TODO: set self.is_hardware_triggered from pv
        super(AndorDriverPart, self).configure(
            context, completed_steps, steps_to_do, generator, **kwargs)
        child = context.block_view(self.mri)
        # Need to reset acquirePeriod as it's sometimes wrong
        child.acquirePeriod.put_value(generator.duration)
