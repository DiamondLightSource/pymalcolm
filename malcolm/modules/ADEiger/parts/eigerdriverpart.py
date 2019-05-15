from annotypes import add_call_types
from malcolm.modules.ADCore.parts import DetectorDriverPart
from malcolm.core import PartRegistrar
from malcolm.modules.scanning.hooks import AContext, \
    PostRunArmedHook, PostRunReadyHook


class EigerDriverPart(DetectorDriverPart):
    """ Overrides default AD behaviour because the Eiger AD support
        does not count frames when Odin is consuming the frames."""

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(EigerDriverPart, self).setup(registrar)
        self.register_hooked((PostRunReadyHook,), self.post_run_ready)
        self.register_hooked((PostRunArmedHook,), self.post_run_armed)

    @add_call_types
    def run(self, context):
        # type: (AContext) -> None
        # this override removes the subscription to the array counter
        # which is never updated by Eiger
        pass

    @add_call_types
    def post_run_ready(self, context):
        # type: (AContext) -> None
        # currently the AD support does not know how many frames the detector
        # has taken and never finishes the Acquire. We know that the file
        # writer has completed at post run so stop the AD Acquisition
        child = context.block_view(self.mri)
        child.stop()

        context.wait_all_futures(self.actions.start_future)
        super(EigerDriverPart, self).post_run_ready(context)

    @add_call_types
    def post_run_armed(self, context):
        # type: (AContext) -> None
        # Stop the acquisition as per post_run_ready
        child = context.block_view(self.mri)
        child.stop()

        context.wait_all_futures(self.actions.start_future)
