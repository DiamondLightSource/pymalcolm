from annotypes import Anno, add_call_types, Any

from malcolm.core import PartRegistrar
from malcolm.modules import ADCore, scanning, builtin

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri

with Anno("Directory to write data to"):
    AFileDir = str


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

    # Allow camelCase as arguments are serialized
    # noinspection PyPep8Naming
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

        # Calculate the readout time
        child = context.block_view(self.mri)

        if child.andorFrameTransferMode.value:
            # Set exposure to zero and use accumulation period for readout time
            child.exposure.put_value(0.0)
            child.acquirePeriod.put_value(0.0)
            readout_time = child.andorAccumulatePeriod.value
            # We need to use the custom DeadTimeInfoPart to handle frame
            # transfer mode
            info_cls = Andor2FrameTransferModeDeadTimeInfo
        else:
            # Behaves like a "normal" detector
            child.exposure.put_value(generator.duration)
            child.acquirePeriod.put_value(generator.duration)
            # Readout time can be approximated from difference in exposure time
            # and acquire period
            readout_time = child.acquirePeriod.value - child.exposure.value
            # It seems that the difference between acquirePeriod and exposure
            # doesn't tell the whole story, we seem to need an additional bit
            # of readout (or something) time on top
            fudge_factor = generator.duration * 0.004 + 0.001
            readout_time = readout_time + fudge_factor
            # Otherwise we can behave like a "normal" detector
            info_cls = ADCore.infos.ExposureDeadtimeInfo

        # Create an ExposureInfo to pass to the superclass
        info = info_cls(
            readout_time, frequency_accuracy=50, min_exposure=0.0)
        exposure = info.calculate_exposure(generator.duration, exposure)
        self.exposure.set_value(exposure)
        part_info[""] = [info]

        super(AndorDriverPart, self).configure(
            context, completed_steps, steps_to_do, part_info, generator,
            fileDir, **kwargs)


class Andor2FrameTransferModeDeadTimeInfo(ADCore.infos.ExposureDeadtimeInfo):
    def calculate_exposure(self, duration, exposure=0.0):
        """With frame transfer mode enabled, the exposure is the time between
        triggers. The epics 'acquireTime' actually becomes the User Defined
        delay before acquisition start after the trigger. The duration floor
        becomes the readout time.
        """
        assert duration > self.readout_time, \
            "The duration: %s has to be longer than the Andor 2 readout " \
            "time: %s." % (duration, self.readout_time)
        exposure = 0.0
        return exposure
