from annotypes import Anno, add_call_types, Any

from malcolm.modules import ADCore, scanning

with Anno("Sample frequency of ADC signal in Hz"):
    ASampleFreq = float


class ReframePluginPart(ADCore.parts.DetectorDriverPart):
    def __init__(self, name, mri, sample_freq=10000.0):
        # type: (ADCore.parts.APartName, ADCore.parts.AMri, ASampleFreq) -> None
        super(ReframePluginPart, self).__init__(name, mri)
        self.sample_freq = sample_freq
        # Hooks
        self.register_hooked(scanning.hooks.ValidateHook, self.validate)

    @add_call_types
    def validate(self, generator):
        # type: (scanning.hooks.AGenerator) -> None
        exposure = generator.duration
        assert exposure > 0, \
            "Duration %s for generator must be >0 to signify fixed exposure" \
            % exposure
        nsamples = int(exposure * self.sample_freq) - 1
        assert nsamples > 0, \
            "Duration %s for generator gives < 1 ADC sample" % exposure

    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> None
        nsamples = int(generator.duration * self.sample_freq) - 1
        super(ReframePluginPart, self).configure(
            context, completed_steps, steps_to_do, part_info, generator,
            postCount=nsamples, **kwargs)
