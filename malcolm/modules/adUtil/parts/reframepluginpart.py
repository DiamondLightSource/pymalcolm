from annotypes import Anno, add_call_types, Any

from malcolm.core import PartRegistrar, Context
from malcolm.modules import ADCore, scanning, builtin

with Anno("Sample frequency of ADC signal in Hz"):
    ASampleFreq = float

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = ADCore.parts.APartName
AMri = ADCore.parts.AMri


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save('postCount')
class ReframePluginPart(ADCore.parts.DetectorDriverPart):
    def __init__(self, name, mri, sample_freq=10000.0):
        # type: (APartName, AMri, ASampleFreq) -> None
        super(ReframePluginPart, self).__init__(name, mri)
        self.sample_freq = sample_freq

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(ReframePluginPart, self).setup(registrar)
        # Hooks
        registrar.hook(scanning.hooks.ValidateHook, self.on_validate)

    @add_call_types
    def on_validate(self, generator):
        # type: (scanning.hooks.AGenerator) -> None
        exposure = generator.duration
        assert exposure > 0, \
            "Duration %s for generator must be >0 to signify fixed exposure" \
            % exposure
        nsamples = int(exposure * self.sample_freq) - 1
        assert nsamples > 0, \
            "Duration %s for generator gives < 1 ADC sample" % exposure

    def setup_detector(self,
                       context,  # type: Context
                       completed_steps,  # type: scanning.hooks.ACompletedSteps
                       steps_to_do,  # type: scanning.hooks.AStepsToDo
                       duration,  # type: int
                       part_info,  # type: scanning.hooks.APartInfo
                       **kwargs  # type: Any
                       ):
        # type: (...) -> None
        nsamples = int(duration * self.sample_freq) - 1
        super(ReframePluginPart, self).setup_detector(
            context, completed_steps, steps_to_do, duration, part_info,
            postCount=nsamples, **kwargs)
