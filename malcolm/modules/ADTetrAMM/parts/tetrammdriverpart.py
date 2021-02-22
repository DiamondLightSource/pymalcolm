from math import ceil

from annotypes import add_call_types

from malcolm.core import NumberMeta, PartRegistrar, Widget
from malcolm.modules import ADCore, builtin, scanning

APartName = builtin.parts.APartName
AMri = builtin.parts.AMri
TETRAMM_BASE_FREQ = 100000.0
TETRAMM_MIN_VALUES_PER_READ = 5


@builtin.util.no_save("numImagesPerSeries", "valuesPerRead")
class TetrAMMDriverPart(ADCore.parts.DetectorDriverPart):
    def __init__(self, name: APartName, mri: AMri) -> None:
        super().__init__(name, mri)
        self.targetSamplesPerFrame = NumberMeta(
            "uint32",
            "Target samples that each frame contains, "
            "0 for maximum, -1 for not controlling it.",
            tags=[Widget.TEXTINPUT.tag()],
        ).create_attribute_model()

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        registrar.add_attribute_model(
            "targetSamplesPerFrame",
            self.targetSamplesPerFrame,
            self.targetSamplesPerFrame.set_value,
        )
        registrar.hook(scanning.hooks.PostRunReadyHook, self.on_post_run_ready)
        registrar.hook(scanning.hooks.PostRunArmedHook, self.on_post_run_armed)
        registrar.hook(scanning.hooks.PostConfigureHook, self.on_post_configure)

    @add_call_types
    def on_post_configure(self, context: scanning.hooks.AContext):
        child = context.block_view(self.mri)
        if self.targetSamplesPerFrame.value == 0:
            child.valuesPerRead.put_value(TETRAMM_MIN_VALUES_PER_READ)
        elif self.targetSamplesPerFrame.value > 0:
            values_per_read = ceil(
                TETRAMM_BASE_FREQ
                * child.exposure.value
                / self.targetSamplesPerFrame.value
            )
            values_per_read = max(values_per_read, TETRAMM_MIN_VALUES_PER_READ)
            child.valuesPerRead.put_value(values_per_read)

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        # this override stops waiting on the start_future as we have to press
        # stop in post_run below
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
