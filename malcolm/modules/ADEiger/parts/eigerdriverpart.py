from annotypes import add_call_types, Any

from malcolm.core import PartRegistrar
from malcolm.modules import ADCore, scanning, builtin


@builtin.util.no_save('numImagesPerSeries')
class EigerDriverPart(ADCore.parts.DetectorDriverPart):
    """ Overrides default AD behaviour because the Eiger AD support
        does not count frames when Odin is consuming the frames."""

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(EigerDriverPart, self).setup(registrar)
        registrar.hook(
            scanning.hooks.PostRunReadyHook, self.post_run_ready)
        registrar.hook(
            scanning.hooks.PostRunArmedHook, self.post_run_armed)

    # Allow CamelCase as fileDir parameter will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  fileDir,  # type: scanning.hooks.AFileDir
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> None
        super(EigerDriverPart, self).configure(
            context, completed_steps, steps_to_do, part_info, generator,
            fileDir, numImagesPerSeries=1, **kwargs)
        child = context.block_view(self.mri)
        child.when_value_matches("fanStateReady", 1)

    @add_call_types
    def run(self, context):
        # type: (scanning.hooks.AContext) -> None
        # this override removes the subscription to the array counter
        # which is never updated by Eiger
        pass

    @add_call_types
    def post_run_ready(self, context):
        # type: (scanning.hooks.AContext) -> None
        # currently the AD support does not know how many frames the detector
        # has taken and never finishes the Acquire. We know that the file
        # writer has completed at post run so stop the AD Acquisition
        child = context.block_view(self.mri)
        child.stop()
        context.wait_all_futures(self.actions.start_future)

    @add_call_types
    def post_run_armed(self, context):
        # type: (scanning.hooks.AContext) -> None
        # Stop the acquisition as per post_run_ready
        # TODO: this should call configure too, will fail for 3D scans at
        # present
        child = context.block_view(self.mri)
        child.stop()
        context.wait_all_futures(self.actions.start_future)
