from typing import Any

from annotypes import Anno, add_call_types

from malcolm.core import Context, PartRegistrar
from malcolm.modules import ADCore, builtin, scanning

with Anno("Sample frequency of ADC signal in Hz"):
    ASampleFreq = float

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = ADCore.parts.APartName
AMri = ADCore.parts.AMri


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save("postCount")
class ReframePluginPart(ADCore.parts.DetectorDriverPart):
    def __init__(
        self, name: APartName, mri: AMri, sample_freq: ASampleFreq = 10000.0
    ) -> None:
        super().__init__(name, mri)
        self.sample_freq = sample_freq

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ValidateHook, self.on_validate)

    @add_call_types
    def on_validate(
        self, context: scanning.hooks.AContext, generator: scanning.hooks.AGenerator
    ) -> None:
        child = context.block_view(self.mri)
        exposure = generator.duration
        assert (
            exposure > 0
        ), f"Duration {exposure} for generator must be >0 to signify fixed exposure"
        if child.averageSamples.value == "Yes":
            min_exposure = 1.0 / self.sample_freq
            assert (
                exposure >= min_exposure
            ), f"Duration {exposure} too short for sample frequency {self.sample_freq}"
        else:
            assert (
                self._number_of_adc_samples(exposure) > 0
            ), f"Duration {exposure} for generator gives < 1 ADC sample"

    def _number_of_adc_samples(self, exposure: float):
        return int(exposure * self.sample_freq) - 1

    def setup_detector(
        self,
        context: Context,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        duration: float,
        part_info: scanning.hooks.APartInfo,
        **kwargs: Any,
    ) -> None:
        if completed_steps == 0:
            # This is an initial configure, so reset arrayCounter to 0
            array_counter = 0
            self.done_when_reaches = steps_to_do
        else:
            # This is rewinding or setting up for another batch,
            # skip to a uniqueID that has not been produced yet
            array_counter = self.done_when_reaches
            self.done_when_reaches += steps_to_do
        self.uniqueid_offset = completed_steps - array_counter

        child = context.block_view(self.mri)

        for k, v in dict(
            arrayCounter=array_counter,
            imageMode="Multiple",
            numImages=steps_to_do,
            arrayCallbacks=True,
        ).items():
            if k not in kwargs and k in child:
                kwargs[k] = v

        # Ignore exposure time attribute
        kwargs.pop("exposure", None)

        child.put_attribute_values(kwargs)

        # Check if samples will be averaged to a single point per channel
        if child.averageSamples.value == "Yes":
            child.postCount.put_value(0)
        else:
            # Set number of post-trigger samples
            post_trigger_samples = int(duration * self.sample_freq) - 1
            child.postCount.put_value(post_trigger_samples)
