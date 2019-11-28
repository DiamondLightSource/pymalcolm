from __future__ import division

from annotypes import Anno, add_call_types

from malcolm.core import Part, NumberMeta, Widget, config_tag, APartName, \
    PartRegistrar, Display
from ..infos import ExposureDeadtimeInfo, ParameterTweakInfo
from ..util import exposure_attribute
from ..hooks import ReportStatusHook, ValidateHook, ConfigureHook, \
    AGenerator, AExposure, UInfos

readout_desc = \
    "Subtract this time from frame duration when calculating exposure"
with Anno(readout_desc):
    AInitialReadoutTime = float
frequency_accuracy_desc = \
    "In ppm. Subtract duration*this/1e6 when calculating exposure"
with Anno(frequency_accuracy_desc):
    AInitialAccuracy = float
with Anno("The minimum exposure time this detector will accept"):
    AMinExposure = float

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName


class ExposureDeadtimePart(Part):
    def __init__(self,
                 name,  # type: APartName
                 initial_readout_time=0.0,  # type: AInitialReadoutTime
                 initial_frequency_accuracy=50.0,  # type: AInitialAccuracy
                 min_exposure=0.0  # type: AMinExposure
                 ):
        # type: (...) -> None
        super(ExposureDeadtimePart, self).__init__(name)
        self.readout_time = NumberMeta(
            "float64", readout_desc,
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
            display=Display(precision=6, units="s")
        ).create_attribute_model(initial_readout_time)
        self.frequency_accuracy = NumberMeta(
            "float64", frequency_accuracy_desc,
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
            display=Display(precision=3, units="ppm")
        ).create_attribute_model(initial_frequency_accuracy)
        self.min_exposure = min_exposure
        self.exposure = exposure_attribute(min_exposure)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(ExposureDeadtimePart, self).setup(registrar)
        # Hooks
        registrar.hook(ReportStatusHook, self.on_report_status)
        registrar.hook(ValidateHook, self.on_validate)
        registrar.hook(ConfigureHook, self.on_configure)
        # Attributes
        registrar.add_attribute_model(
            "readoutTime", self.readout_time, self.readout_time.set_value)
        registrar.add_attribute_model(
            "frequencyAccuracy", self.frequency_accuracy,
            self.frequency_accuracy.set_value)
        registrar.add_attribute_model("exposure", self.exposure)
        # Tell the controller to expose some extra configure parameters
        registrar.report(ConfigureHook.create_info(
            self.on_configure))

    @add_call_types
    def on_report_status(self):
        # type: () -> UInfos
        # Make an info so we can pass it to the detector
        info = ExposureDeadtimeInfo(
            self.readout_time.value, self.frequency_accuracy.value,
            self.min_exposure)
        return info

    @add_call_types
    def on_validate(self, generator, exposure=0.0):
        # type: (AGenerator, AExposure) -> UInfos
        info = self.on_report_status()
        new_exposure = info.calculate_exposure(generator.duration, exposure)
        if new_exposure != exposure:
            return ParameterTweakInfo("exposure", new_exposure)

    @add_call_types
    def on_configure(self, exposure=0.0):
        # type: (AExposure) -> None
        self.exposure.set_value(exposure)
