from malcolm.modules import ADCore, scanning


class ExcaliburDriverPart(ADCore.parts.DetectorDriverPart):
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  generator,  # type: scanning.hooks.AGenerator
                  **kwargs  # type: **scanning.hooks.Any
                  ):
        # type: (...) -> None
        child = context.block_view(self.mri)
        super(ExcaliburDriverPart, self).configure(
            context, completed_steps, steps_to_do, generator, **kwargs)
