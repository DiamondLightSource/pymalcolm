from malcolm.core import method_takes
from malcolm.modules.builtin.parts import StatefulChildPart
from malcolm.modules.scanning.controllers import RunnableController
from .pandablockschildpart import PandABlocksChildPart


class PandABlocksDriverPart(StatefulChildPart, PandABlocksChildPart):
    # Stored futures
    start_future = None

    @RunnableController.Reset
    def reset(self, context):
        super(PandABlocksDriverPart, self).reset(context)
        self.abort(context)

    @RunnableController.Configure
    @RunnableController.PostRunReady
    @RunnableController.Seek
    @method_takes()
    def configure(self, context, completed_steps, steps_to_do, part_info):
        child = context.block_view(self.params.mri)
        context.unsubscribe_all()
        child.put_attribute_values(dict(
            imageMode="Multiple",
            numImages=steps_to_do,
            arrayCounter=completed_steps,
            arrayCallbacks=True))
        self.start_future = child.start_async()

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, context, update_completed_steps):
        child = context.block_view(self.params.mri)
        child.arrayCounter.subscribe_value(update_completed_steps, self)
        context.wait_all_futures(self.start_future)

    @RunnableController.Abort
    @RunnableController.Pause
    def abort(self, context):
        child = context.block_view(self.params.mri)
        child.stop()

