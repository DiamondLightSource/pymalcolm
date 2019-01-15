from annotypes import add_call_types, Any

from malcolm.modules import ADCore, scanning
from malcolm.modules.ADCore.infos import ExposureDeadtimeInfo


class AndorDriverPart(ADCore.parts.DetectorDriverPart):
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
        child = context.block_view(self.mri)
        readout_time = self.get_readout_time(child, generator.duration)

        # Create an ExposureInfo to pass to the superclass
        part_info[""] = [ExposureDeadtimeInfo(
            readout_time, frequency_accuracy=50)]
        super(AndorDriverPart, self).configure(
            context, completed_steps, steps_to_do, part_info, generator,
            **kwargs)

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
