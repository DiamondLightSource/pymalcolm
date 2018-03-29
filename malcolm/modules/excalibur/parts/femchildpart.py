from malcolm.modules import scanning, ADCore


class FemChildPart(ADCore.parts.DatasetRunnableChildPart):
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  **kwargs  # type: **scanning.hooks.Any
                  ):
        # type: (...) -> None
        # Throw away the dataset info the superclass returns
        super(FemChildPart, self).configure(context, **kwargs)
        # Sleep after configuration - recommended to allow at least 1s after
        # starting Excalibur before taking first frame following testing on J13.
        # Otherwise FEM1 may not be ready and will drop a frame.
        context.sleep(1.0)
