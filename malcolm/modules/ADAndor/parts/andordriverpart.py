from annotypes import add_call_types, Any

from malcolm.modules import ADCore, scanning
from malcolm.modules.ADCore.infos import ExposureDeadtimeInfo
import cothread


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

        # Get readout time
        readout_time = self.get_readout_time(child)

        # Frequency accuracy in PPM (set to 0 as we use a fixed offset)
        frequency_accuracy = 0.0

        # Additional buffer to offset acquirePeriod from generator duration
        additional_buffer_time = 0.001

        # Use ExposureDeadtimeInfo
        exposure_info = ExposureDeadtimeInfo(readout_time, frequency_accuracy)
        kwargs["exposure"] = exposure_info.calculate_exposure(
            generator.duration) - additional_buffer_time

        self.actions.setup_detector(
            context, completed_steps, steps_to_do, **kwargs)

        # Set acquire period to exposure time (driver will set to minimum allowed)
        child.acquirePeriod.put_value(kwargs["exposure"])

        if self.is_hardware_triggered:
            # Start now if we are hardware triggered
            self.actions.arm_detector(context)

    def get_readout_time(self, child):
        """Calculate the readout time of the detector from the EPICS driver
            - Set exposure and acquire period to same value
            - Acquire period will be set to lowest acceptable value
            - Difference will be readout time (this value is affected by detector settings)
        """
        exposure_time_trial = 1.0
        child.exposure.put_value(exposure_time_trial)
        child.acquirePeriod.put_value(exposure_time_trial)

        exposure_time = child.exposure.value
        acquire_period = child.acquirePeriod.value
        readout_time = acquire_period - exposure_time

        return readout_time
