from annotypes import add_call_types

from malcolm.core import Context, PartRegistrar
from malcolm.modules import ADCore, builtin, scanning


@builtin.util.no_save("numImagesPerSeries")
class EigerDriverPart(ADCore.parts.DetectorDriverPart):
    """Overrides default AD behaviour because the Eiger AD support
    does not count frames when Odin is consuming the frames."""

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        registrar.hook(scanning.hooks.PostRunReadyHook, self.on_post_run_ready)
        registrar.hook(scanning.hooks.PostRunArmedHook, self.on_post_run_armed)

    def arm_detector(self, context: Context) -> None:
        child = context.block_view(self.mri)
        child.numImagesPerSeries.put_value(1)
        super().arm_detector(context)
        # Wait for the fan to be ready before returning from configure
        child.when_value_matches("fanStateReady", 1)

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        # this override removes the subscription to the array counter
        # which is never updated by Eiger
        pass

    @add_call_types
    def on_post_run_ready(self, context: scanning.hooks.AContext) -> None:
        # currently the AD support does not know how many frames the detector
        # has taken and never finishes the Acquire. We know that the file
        # writer has completed at post run so stop the AD Acquisition
        child = context.block_view(self.mri)
        child.stop()
        context.wait_all_futures(self.start_future)

    @add_call_types
    def on_post_run_armed(self, context: scanning.hooks.AContext) -> None:
        # Stop the acquisition as per post_run_ready
        # TODO: this should call configure too, will fail for 3D scans at
        # present
        child = context.block_view(self.mri)
        child.stop()
        context.wait_all_futures(self.start_future)
