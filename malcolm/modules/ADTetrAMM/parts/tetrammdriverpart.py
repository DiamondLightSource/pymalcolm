from annotypes import add_call_types

from malcolm.core import PartRegistrar, Context
from malcolm.modules import ADCore, scanning, builtin


@builtin.util.no_save('numImagesPerSeries')
class TetrAMMDriverPart(ADCore.parts.DetectorDriverPart):
    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(TetrAMMDriverPart, self).setup(registrar)
        registrar.hook(
            scanning.hooks.PostRunReadyHook, self.on_post_run_ready)
        registrar.hook(
            scanning.hooks.PostRunArmedHook, self.on_post_run_armed)

    @add_call_types
    def on_run(self, context):
        # type: (scanning.hooks.AContext) -> None
        # this override stops waiting on the start_future as we have to press
        # stop in post_run below
        pass

    @add_call_types
    def on_post_run_ready(self, context):
        # type: (scanning.hooks.AContext) -> None
        # currently the AD support does not know how many frames the detector
        # has taken and never finishes the Acquire. We know that the file
        # writer has completed at post run so stop the AD Acquisition
        child = context.block_view(self.mri)
        child.stop()
        context.wait_all_futures(self.start_future)

    @add_call_types
    def on_post_run_armed(self, context):
        # type: (scanning.hooks.AContext) -> None
        # Stop the acquisition as per post_run_ready
        # TODO: this should call configure too, will fail for 3D scans at
        # present
        child = context.block_view(self.mri)
        child.stop()
        context.wait_all_futures(self.start_future)
