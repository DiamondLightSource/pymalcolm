from annotypes import Anno, add_call_types, Any

from malcolm.modules import ADCore, scanning
from malcolm.modules.ADCore.infos import ExposureDeadtimeInfo

with Anno("Directory to write data to"):
    AFileDir = str


class AndorDriverPart(ADCore.parts.DetectorDriverPart):
    @add_call_types
    def configure(self,
                  context,  # type: scanning.hooks.AContext
                  completed_steps,  # type: scanning.hooks.ACompletedSteps
                  steps_to_do,  # type: scanning.hooks.AStepsToDo
                  part_info,  # type: scanning.hooks.APartInfo
                  generator,  # type: scanning.hooks.AGenerator
                  fileDir,  # type: AFileDir
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
            info_cls = ExposureDeadtimeInfo

        # Place an ExposureDeadtimeInfo into the part_info so that our
        # superclass call picks it up and sets acquireTime and exposure
        # accordingly
        part_info[""] = [info_cls(readout_time, frequency_accuracy=50)]

        super(AndorDriverPart, self).configure(
            context, completed_steps, steps_to_do, part_info, generator,
            fileDir, **kwargs)


class Andor2FrameTransferModeDeadTimeInfo(ExposureDeadtimeInfo):
    def __init__(self, readout_time, frequency_accuracy):
        super(Andor2FrameTransferModeDeadTimeInfo, self).__init__(
            readout_time, frequency_accuracy)

    def calculate_exposure(self, duration):
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
