from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.parts import RunnableChildPart


class PmacRunnableChildPart(RunnableChildPart):
    # TODO: not sure if this is still needed to reset triggers on pause?
    # Think it probably is because we need to reset triggers before rearming
    # detectors
    @RunnableController.Pause
    def pause(self, context):
        child = context.block_view(self.params.mri)
        child.pause()
