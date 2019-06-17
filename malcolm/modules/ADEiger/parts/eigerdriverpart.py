from annotypes import add_call_types, Any, Union
from malcolm.modules.ADCore.parts import DetectorDriverPart, \
    AFileDir, USoftTriggerModes, AMainDatasetUseful
from malcolm.core import PartRegistrar, APartName
from malcolm.modules.scanning.hooks import AContext, \
    AStepsToDo, ACompletedSteps, APartInfo, PostRunArmedHook, PostRunReadyHook
from malcolm.modules.scanning.util import AGenerator
from malcolm.modules.builtin.parts import AMri
from malcolm.modules.ADCore.util import APartRunsOnWindows
from malcolm.modules.builtin.util import no_save


@no_save('numImagesPerSeries')
class EigerDriverPart(DetectorDriverPart):
    """ Overrides default AD behaviour because the Eiger AD support
        does not count frames when Odin is consuming the frames."""

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(EigerDriverPart, self).setup(registrar)
        self.register_hooked((PostRunReadyHook,), self.post_run_ready)
        self.register_hooked((PostRunArmedHook,), self.post_run_armed)

    # Allow CamelCase as fileDir parameter will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: AContext
                  completed_steps,  # type: ACompletedSteps
                  steps_to_do,  # type: AStepsToDo
                  part_info,  # type: APartInfo
                  generator,  # type: AGenerator
                  fileDir,  # type: AFileDir
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
