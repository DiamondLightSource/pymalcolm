from annotypes import Anno, Any

from malcolm.core import PartRegistrar, Context, NumberMeta
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
        # Tell the controller to pass "exposure" to configure
        info = scanning.infos.ConfigureParamsInfo(
            metas=dict(exposure=NumberMeta.from_annotype(
                scanning.hooks.AExposure, writeable=True)),
            required=[],
            defaults=dict(exposure=0.0))
        registrar.report(info)

    def setup_detector(self,
                       context,  # type: Context
                       completed_steps,  # type: scanning.hooks.ACompletedSteps
                       steps_to_do,  # type: scanning.hooks.AStepsToDo
                       duration,  # type: float
                       part_info,  # type: scanning.hooks.APartInfo
                       **kwargs  # type: Any
                       ):
        # Calculate the readout time
        child = context.block_view(self.mri)
        if child.andorFrameTransferMode.value:
            # Set exposure to zero and use accumulation period for readout time
            exposure = 0.0
            child.exposure.put_value(exposure)
            child.acquirePeriod.put_value(exposure)
            readout_time = child.andorAccumulatePeriod.value
            # With frame transfer mode enabled, the exposure is the time between
            # triggers. The epics 'acquireTime' (exposure) actually becomes the
            # User Defined delay before acquisition start after the trigger. The
            # duration floor becomes the readout time
            assert duration > readout_time, \
                "The duration: %s has to be longer than the Andor 2 readout " \
                "time: %s." % (duration, readout_time)
            period = readout_time
        else:
            # Behaves like a "normal" detector
            child.exposure.put_value(duration)
            child.acquirePeriod.put_value(duration)
            # Readout time can be approximated from difference in exposure time
            # and acquire period
            readout_time = child.acquirePeriod.value - child.exposure.value
            # Calculate the adjusted exposure time
            (exposure, period) = \
                self.get_adjusted_exposure_time_and_acquire_period(
                    duration,
                    readout_time,
                    kwargs.get("exposure", 0))

        # The real exposure
        self.exposure.set_value(exposure)
        kwargs['exposure'] = exposure

        super(AndorDriverPart, self).setup_detector(
            context,
            completed_steps,
            steps_to_do,
            duration,
            part_info,
            **kwargs)

        child.acquirePeriod.put_value(period)

    def get_adjusted_exposure_time_and_acquire_period(
            self,
            duration,  # type: float
            readout_time,  # type: float
            exposure_time  # type: float
            ):
        # type: (...) -> (float, float)
        # It seems that the difference between acquirePeriod and exposure
        # doesn't tell the whole story, we seem to need an additional bit
        # of readout (or something) time on top
        readout_time += self.get_additional_readout_factor(duration)
        # Otherwise we can behave like a "normal" detector
        info = scanning.infos.ExposureDeadtimeInfo(
            readout_time, frequency_accuracy=50, min_exposure=0.0)
        exposure_time = info.calculate_exposure(
            duration, exposure_time)
        acquire_period = exposure_time + readout_time
        return exposure_time, acquire_period

    @staticmethod
    def get_additional_readout_factor(duration):
        # type: (float) -> float
        return duration * 0.004 + 0.001
