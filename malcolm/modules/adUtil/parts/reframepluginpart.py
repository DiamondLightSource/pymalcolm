from typing import Any

from annotypes import Anno, add_call_types

from malcolm.core import Context, PartRegistrar
from malcolm.modules import ADCore, builtin, scanning

with Anno("Sample frequency of ADC signal in Hz"):
    ASampleFreq = float

with Anno("Is the input trigger gated?"):
    AGatedTrigger = bool

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = ADCore.parts.APartName
AMri = ADCore.parts.AMri


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save("postCount", "averageSamples")
class ReframePluginPart(ADCore.parts.DetectorDriverPart):
    def __init__(
        self,
        name: APartName,
        mri: AMri,
        sample_freq: ASampleFreq = 10000.0,
        gated_trigger: AGatedTrigger = False,
    ) -> None:
        super().__init__(name, mri, soft_trigger_modes="Always On")
        self.sample_freq = sample_freq
        self.gated_trigger = gated_trigger

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ValidateHook, self.on_validate)

    @add_call_types
    def on_validate(self, generator: scanning.hooks.AGenerator) -> None:
        duration = generator.duration
        assert (
            duration > 0
        ), f"Generator duration of {duration} must be > 0 to signify fixed exposure"
        assert (
            self._number_of_adc_samples(duration) > 0
        ), f"Generator duration of {duration} gives < 1 ADC sample"

    def _number_of_adc_samples(self, generator_duration: float):
        return int(generator_duration * self.sample_freq)

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

        # Calculate number of samples
        post_trigger_samples = self._number_of_adc_samples(duration)
        if self.is_hardware_triggered:
            if self.gated_trigger:
                # Gated signal is responsible for number of samples
                post_trigger_samples = 0
                # We also need averaging to ensure we get consistent frame dimensions
                child.averageSamples.put_value("Yes")
            else:
                # For getting just start triggers, ensure we do not miss one
                post_trigger_samples -= 1
                assert (
                    post_trigger_samples > 0
                ), f"Generator duration {duration} too short for start triggers"
        else:
            # Need triggerOffCondition to be Always On for Software triggers
            assert (
                child.triggerOffCondition.value == "Always On"
            ), "Software triggering requires off condition to be 'Always On'"
        child.postCount.put_value(post_trigger_samples)
