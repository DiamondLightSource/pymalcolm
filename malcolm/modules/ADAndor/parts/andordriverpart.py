from annotypes import add_call_types, Any

from malcolm.core import PartRegistrar
from malcolm.modules import ADCore, scanning, builtin

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


class AndorDriverPart(ADCore.parts.DetectorDriverPart):
    def __init__(self, name, mri):
        # type: (APartName, AMri) -> None
        super(AndorDriverPart, self).__init__(name, mri, soft_trigger_modes=[
                "Internal", "Software"])
        self.exposure = scanning.util.exposure_attribute(min_exposure=0.0)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(AndorDriverPart, self).setup(registrar)
        # Attributes
        registrar.add_attribute_model("exposure", self.exposure)
        # Tell the controller to expose some extra configure parameters
        registrar.report(scanning.hooks.ConfigureHook.create_info(
            self.configure))

    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  fileDir,  # type: scanning.hooks.AFileDir
                  exposure=0.0,  # type: scanning.hooks.AExposure
                  **kwargs  # type: **Any
                  ):
        # type: (...) -> None
        child = context.block_view(self.mri)
        readout_time = self.get_readout_time(child, generator.duration)

        # Create an ExposureInfo to pass to the superclass
        info = ADCore.infos.ExposureDeadtimeInfo(
            readout_time, frequency_accuracy=50, min_exposure=0.0)
        exposure = info.calculate_exposure(generator.duration, exposure)
        self.exposure.set_value(exposure)
        part_info[""] = [info]
        super(AndorDriverPart, self).configure(
            context, completed_steps, steps_to_do, part_info, generator,
            fileDir, exposure=exposure, **kwargs)

    def get_readout_time(self, child, duration):
        """Calculate the readout time of the detector from the EPICS driver:

        - Set exposure and acquire period to same value
        - Acquire period will be set to lowest acceptable value
        - Difference will be readout time (this value is affected by
          detector settings)
        """
        child.exposure.put_value(duration)
        child.acquirePeriod.put_value(duration)
        readout_time = child.acquirePeriod.value - child.exposure.value
        # It seems that the difference between acquirePeriod and exposure
        # doesn't tell the whole story, we seem to need an additional bit
        # of readout (or something) time on top
        fudge_factor = duration * 0.004 + 0.001
        return readout_time + fudge_factor
