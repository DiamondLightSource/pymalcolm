from typing import Any, Tuple

from annotypes import Anno, add_call_types
from scanpointgenerator import CompoundGenerator

from malcolm.core import NumberMeta, PartRegistrar
from malcolm.modules import ADCore, builtin, scanning
from malcolm.modules.ADCore.parts.detectordriverpart import AMinAcquirePeriod
from malcolm.modules.scanning.util import AFramesPerStep, exposure_attribute

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri

with Anno("Directory to write data to"):
    AFileDir = str


class AndorDriverPart(ADCore.parts.DetectorDriverPart):
    def __init__(
        self, name: APartName, mri: AMri, min_acquire_period: AMinAcquirePeriod = 0.0
    ) -> None:
        super().__init__(
            name,
            mri,
            soft_trigger_modes=["Internal", "Software"],
            min_acquire_period=min_acquire_period,
        )
        self.exposure = exposure_attribute(min_exposure=0.0)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Validate hook for exposure time
        registrar.hook(scanning.hooks.ValidateHook, self.on_validate)
        # Attributes
        registrar.add_attribute_model("exposure", self.exposure)
        # Tell the controller to pass "exposure" and "frames_per_step" to configure
        info = scanning.infos.ConfigureParamsInfo(
            metas=dict(
                exposure=NumberMeta.from_annotype(
                    scanning.hooks.AExposure, writeable=True
                ),
                frames_per_step=NumberMeta.from_annotype(
                    AFramesPerStep, writeable=False
                ),
            ),
            required=[],
            defaults=dict(exposure=0.0, frames_per_step=1),
        )
        registrar.report(info)

    @add_call_types
    def on_validate(
        self,
        context: scanning.hooks.AContext,
        generator: scanning.hooks.AGenerator,
        exposure: scanning.hooks.AExposure = 0.0,
        frames_per_step: AFramesPerStep = 1,
    ) -> scanning.hooks.UParameterTweakInfos:
        # Get the duration per frame
        duration = generator.duration
        assert (
            duration >= 0
        ), f"Generator duration of {duration} must be >= 0 to signify fixed exposure"
        # As the Andor runnable block does not have an ExposureDeadTimePart, we handle
        # the case where we have been given an exposure time here
        if exposure > 0:
            # Grab the current value of the readout time and hope that the parameters
            # will not change before we actually run configure...
            child = context.block_view(self.mri)
            driver_readout_time = child.andorReadoutTime.value
            # Add the exposure time and multiply up to get the total generator duration
            duration_per_frame = exposure + driver_readout_time
            # Check if we need to guess the duration
            if duration == 0.0:
                serialized = generator.to_dict()
                new_generator = CompoundGenerator.from_dict(serialized)
                # Multiply the duration per frame up
                duration_per_point = duration_per_frame * frames_per_step
                new_generator.duration = duration_per_frame * frames_per_step
                self.log.debug(
                    f"{self.name}: tweaking generator duration from "
                    f"{generator.duration} to {duration_per_point}"
                )
                return scanning.hooks.ParameterTweakInfo("generator", new_generator)
            # Otherwise we just want to check if we can achieve the exposure expected
            else:
                assert duration_per_frame <= duration, (
                    f"{self.name}: cannot achieve exposure of {exposure} with per frame"
                    f" duration of {duration}"
                )
                return None
        # Otherwise just let the DetectorDriverPart validate for us
        else:
            return super().on_validate(generator, frames_per_step=frames_per_step)

    def setup_detector(
        self,
        context: scanning.hooks.AContext,
        completed_steps: scanning.hooks.ACompletedSteps,
        steps_to_do: scanning.hooks.AStepsToDo,
        num_images: int,
        duration: float,
        part_info: scanning.hooks.APartInfo,
        initial_configure: bool = True,
        **kwargs: Any,
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
            assert duration > readout_time, (
                "The duration: %s has to be longer than the Andor 2 readout "
                "time: %s." % (duration, readout_time)
            )
            period = readout_time
        else:
            # Behaves like a "normal" detector
            child.exposure.put_value(duration)
            child.acquirePeriod.put_value(duration)
            # Readout time can be approximated from difference in exposure time
            # and acquire period
            readout_time = child.acquirePeriod.value - child.exposure.value
            # Calculate the adjusted exposure time
            (exposure, period) = self.get_adjusted_exposure_time_and_acquire_period(
                duration, readout_time, kwargs.get("exposure", 0)
            )

        # The real exposure
        self.exposure.set_value(exposure)
        kwargs["exposure"] = exposure

        super().setup_detector(
            context,
            completed_steps,
            steps_to_do,
            num_images,
            duration,
            part_info,
            initial_configure=initial_configure,
            **kwargs,
        )

        child.acquirePeriod.put_value(period)

    def get_adjusted_exposure_time_and_acquire_period(
        self, duration: float, readout_time: float, exposure_time: float
    ) -> Tuple[float, float]:
        # It seems that the difference between acquirePeriod and exposure
        # doesn't tell the whole story, we seem to need an additional bit
        # of readout (or something) time on top
        readout_time += self.get_additional_readout_factor(duration)
        # Otherwise we can behave like a "normal" detector
        info = scanning.infos.ExposureDeadtimeInfo(
            readout_time, frequency_accuracy=50, min_exposure=0.0
        )
        exposure_time = info.calculate_exposure(duration, exposure_time)
        acquire_period = exposure_time + readout_time
        return exposure_time, acquire_period

    @staticmethod
    def get_additional_readout_factor(duration: float) -> float:
        return duration * 0.004 + 0.001
