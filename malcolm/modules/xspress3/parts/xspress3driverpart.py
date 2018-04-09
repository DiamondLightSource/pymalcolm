from annotypes import add_call_types, Any

from malcolm.modules import ADCore, scanning

XSPRESS3_BUFFER = 16384


class Xspress3DriverPart(ADCore.parts.DetectorDriverPart):
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> None
        # TODO: set self.is_hardware_triggered from pv
        if steps_to_do > XSPRESS3_BUFFER:
            # Set the PointsPerRow from the innermost dimension
            gen_num = generator.dimensions[-1].size
            steps_per_row = XSPRESS3_BUFFER // gen_num * gen_num
        else:
            steps_per_row = steps_to_do
        kwargs.update(dict(
            pointsPerRow=steps_per_row,
            # TODO: this goes in config
            triggerMode="Hardware"))
        return super(Xspress3DriverPart, self).configure(
            context, completed_steps, steps_to_do, part_info, generator,
            **kwargs)
