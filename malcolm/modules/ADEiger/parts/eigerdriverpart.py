from annotypes import add_call_types

from malcolm.core import Context, PartRegistrar, APartName, DEFAULT_TIMEOUT, BooleanMeta
from malcolm.modules import ADCore, builtin, scanning

from malcolm.modules.ADCore.parts.detectordriverpart import USoftTriggerModes, AMainDatasetUseful, AVersionRequirement, AMinAcquirePeriod
from malcolm.modules.ADCore.util import APartRunsOnWindows

# Pull re-used annotypes into our namespace in case we are subclassed
AMri = builtin.parts.AMri

@builtin.util.no_save("numImagesPerSeries")
class EigerDriverPart(ADCore.parts.DetectorDriverPart):
    """Overrides default AD behaviour because the Eiger AD support
    does not count frames when Odin is consuming the frames."""

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        writer_mri: AMri,
        soft_trigger_modes: USoftTriggerModes = None,
        main_dataset_useful: AMainDatasetUseful = True,
        runs_on_windows: APartRunsOnWindows = False,
        required_version: AVersionRequirement = None,
        min_acquire_period: AMinAcquirePeriod = 0.0
    ) -> None:
        self.writer_mri = writer_mri
        #self.staleParametersLatch =  BooleanMeta("Latches high on stale parameters PV", ["True", "False"], False).create_attribute_model(False)
        super().__init__(name, mri, soft_trigger_modes, main_dataset_useful, runs_on_windows, required_version, min_acquire_period)



    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        registrar.hook(scanning.hooks.PostRunReadyHook, self.on_post_run_ready)
        registrar.hook(scanning.hooks.PostRunArmedHook, self.on_post_run_armed)

    def arm_detector(self, context: Context) -> None:
        child = context.block_view(self.mri)
        child.numImagesPerSeries.put_value(1)
        child.staleParametersLatch.put_value("Latched")

        child_writer = context.block_view(self.writer_mri)
        
        # Odin reads the filename at the point of arming the detector, not the file writer. Therefore 
        # we wait for the writer to start before starting the detector, as this ensures the filename 
        # has been written. 
        child_writer.when_value_matches("running", True, timeout=DEFAULT_TIMEOUT)

        super().arm_detector(context)
        child.staleParametersLatch.put_value("Clear")
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
        # context.wait_all_futures(self.start_future)

    @add_call_types
    def on_post_run_armed(self, context: scanning.hooks.AContext) -> None:
        # Stop the acquisition as per post_run_ready
        # TODO: this should call configure too, will fail for 3D scans at
        # present
        child = context.block_view(self.mri)
        child.stop()
        # context.wait_all_futures(self.start_future)
