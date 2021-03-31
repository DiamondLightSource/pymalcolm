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
    AInitialReadoutTime = float
frequency_accuracy_desc = "In ppm. Subtract duration*this/1e6 when calculating exposure"
with Anno(frequency_accuracy_desc):
    AInitialAccuracy = float
with Anno("The minimum exposure time this detector will accept"):
    AMinExposure = float

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName


class ExposureDeadtimePart(Part):
    def __init__(
        self,
        name: APartName,
        initial_readout_time: AInitialReadoutTime = 0.0,
        initial_frequency_accuracy: AInitialAccuracy = 50.0,
        min_exposure: AMinExposure = 0.0,
    ) -> None:
        super().__init__(name)
        self.readout_time = NumberMeta(
            "float64",
            readout_desc,
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
            display=Display(precision=6, units="s"),
        ).create_attribute_model(initial_readout_time)
        self.frequency_accuracy = NumberMeta(
            "float64",
            frequency_accuracy_desc,
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
            display=Display(precision=3, units="ppm"),
        ).create_attribute_model(initial_frequency_accuracy)
        self.min_exposure = min_exposure
        self.exposure = exposure_attribute(min_exposure)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(ReportStatusHook, self.on_report_status)
        registrar.hook(ValidateHook, self.on_validate)
        registrar.hook(ConfigureHook, self.on_configure)
        # Attributes
        registrar.add_attribute_model(
            "readoutTime", self.readout_time, self.readout_time.set_value
        )
        registrar.add_attribute_model(
            "frequencyAccuracy",
            self.frequency_accuracy,
            self.frequency_accuracy.set_value,
        )
        registrar.add_attribute_model("exposure", self.exposure)
        # Tell the controller to expose some extra configure parameters
        registrar.report(ConfigureHook.create_info(self.on_configure))

    @add_call_types
    def on_report_status(self) -> UInfos:
        # Make an info so we can pass it to the detector
        info = ExposureDeadtimeInfo(
            self.readout_time.value, self.frequency_accuracy.value, self.min_exposure
        )
        return info

    @add_call_types
    def on_validate(self, generator: AGenerator, exposure: AExposure = 0.0) -> UInfos:
        info = self.on_report_status()
        if generator.duration == 0.0:
            # We need to calculate a new duration
            if exposure > 0:
                # Calculate the minimum acceptable duration
                new_duration = info.calculate_minimum_duration(exposure)
                serialized = generator.to_dict()
                new_generator = CompoundGenerator.from_dict(serialized)
                new_generator.duration = new_duration
                return ParameterTweakInfo("generator", new_generator)
            else:
                # First calculate the minimum possible exposure time
                new_exposure = info.calculate_exposure(generator.duration, exposure)
                # Now calculate minimum generator duration
                new_duration = info.calculate_minimum_duration(new_exposure)
                serialized = generator.to_dict()
                new_generator = CompoundGenerator.from_dict(serialized)
                # Add a tiny fractional amount because of floats being floats
                new_generator.duration = new_duration * (1 + 1e-12)
                # Return the tweaked parameters
                return [
                    ParameterTweakInfo("generator", new_generator),
                    ParameterTweakInfo("exposure", new_exposure),
                ]
        else:
            # We need to calculate the minimum acceptable exposure time
            new_exposure = info.calculate_exposure(generator.duration, exposure)
            if new_exposure != exposure:
                return ParameterTweakInfo("exposure", new_exposure)
            else:
                return None

    @add_call_types
    def on_configure(self, exposure: AExposure = 0.0) -> None:
        self.exposure.set_value(exposure)
