from annotypes import Anno, add_call_types
from scanpointgenerator import CompoundGenerator

from malcolm.core import (
    APartName,
    Display,
    NumberMeta,
    Part,
    PartRegistrar,
    Widget,
    config_tag,
)

from ..hooks import (
    AExposure,
    AGenerator,
    ConfigureHook,
    ReportStatusHook,
    UInfos,
    ValidateHook,
)
from ..infos import ExposureDeadtimeInfo, ParameterTweakInfo
from ..util import exposure_attribute

readout_desc = "Subtract this time from frame duration when calculating exposure"
with Anno(readout_desc):
    AReadoutTime = float
frequency_accuracy_desc = "In ppm. Subtract duration*this/1e6 when calculating exposure"
with Anno(frequency_accuracy_desc):
    AAccuracy = float
with Anno("The minimum exposure time this detector will accept"):
    AMinExposure = float
with Anno("Frames per detector step"):
    ADetectorFramesPerStep = int

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName


class ExposureDeadtimePart(Part):
    def __init__(
        self,
        name: APartName,
        readout_time: AReadoutTime = 0.0,
        frequency_accuracy: AAccuracy = 50.0,
        min_exposure: AMinExposure = 0.0,
    ) -> None:
        super().__init__(name)
        self.readout_time = NumberMeta(
            "float64",
            readout_desc,
            tags=[Widget.TEXTUPDATE.tag(), config_tag()],
            display=Display(precision=6, units="s"),
        ).create_attribute_model(readout_time)
        self.frequency_accuracy = NumberMeta(
            "float64",
            frequency_accuracy_desc,
            tags=[Widget.TEXTUPDATE.tag(), config_tag()],
            display=Display(precision=3, units="ppm"),
        ).create_attribute_model(frequency_accuracy)
        self.min_exposure = min_exposure
        self.exposure = exposure_attribute(min_exposure)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(ReportStatusHook, self.on_report_status)
        registrar.hook(ValidateHook, self.on_validate)
        registrar.hook(ConfigureHook, self.on_configure)
        # Attributes
        registrar.add_attribute_model("readoutTime", self.readout_time)
        registrar.add_attribute_model("frequencyAccuracy", self.frequency_accuracy)
        registrar.add_attribute_model("exposure", self.exposure)
        # Tell the controller to expose some extra configure parameters
        registrar.report(ConfigureHook.create_info(self.on_configure))
        # Tell the controller to expose some extra validate parameters
        registrar.report(ConfigureHook.create_info(self.on_validate))

    @add_call_types
    def on_report_status(self) -> UInfos:
        # Make an info so we can pass it to the detector
        info = ExposureDeadtimeInfo(
            self.readout_time.value, self.frequency_accuracy.value, self.min_exposure
        )
        return info

    @add_call_types
    def on_validate(
        self,
        generator: AGenerator,
        exposure: AExposure = 0.0,
        frames_per_step: ADetectorFramesPerStep = 1,
    ) -> UInfos:
        info = self.on_report_status()
        # Check if we need to calculate a generator duration
        if generator.duration == 0.0:
            if exposure == 0.0:
                # Get minimum exposure time
                exposure = info.calculate_exposure(generator.duration, exposure)
            # Calculate generator duration
            new_duration = info.calculate_minimum_duration(exposure) * frames_per_step
            # Add a tiny fractional amount so we don't run into floating point
            # comparison issues
            new_duration *= 1 + 1e-12
            serialized = generator.to_dict()
            new_generator = CompoundGenerator.from_dict(serialized)
            new_generator.duration = new_duration
            self.log.debug(f"{self.name}: tweaking duration to {new_duration}")
            # Only tweak the duration for now
            return ParameterTweakInfo("generator", new_generator)
        else:
            # Check if we need to tweak the exposure time
            if exposure == 0.0:
                new_exposure = info.calculate_exposure(generator.duration, exposure)
                self.log.debug(f"{self.name}: tweaking exposure to {new_exposure}")
                return ParameterTweakInfo("exposure", new_exposure)
            # Otherwise check the provided parameters are compatible
            else:
                # Check provided exposure against minimum exposure
                min_exposure = info.min_exposure
                assert (
                    exposure >= info.min_exposure
                ), f"{self.name} given exposure {exposure} below min {min_exposure}"
                # Check provided exposure against maximum possible exposure
                max_exposure = info.calculate_maximum_exposure(generator.duration)
                assert exposure <= max_exposure, (
                    f"{self.name} given exposure {exposure} above max {max_exposure} "
                    f"based on a duration per frame of {generator.duration}"
                )
            return None

    @add_call_types
    def on_configure(self, exposure: AExposure = 0.0) -> None:
        self.exposure.set_value(exposure)
