from __future__ import division

from annotypes import Anno, add_call_types

from malcolm.core import Part, NumberMeta, Widget, config_tag, APartName, \
    PartRegistrar
from malcolm.modules import scanning
from ..infos import ExposureDeadtimeInfo

readout_desc = \
    "Subtract this time from frame duration when calculating exposure"
with Anno(readout_desc):
    AInitialReadoutTime = float
frequency_accuracy_desc = \
    "In ppm. Subtract duration*this/1e6 when calculating exposure"
with Anno(frequency_accuracy_desc):
    AInitialAccuracy = float


class ExposureDeadtimePart(Part):
    def __init__(self,
                 name,  # type: APartName
                 initial_readout_time=0.0,  # type: AInitialReadoutTime
                 initial_frequency_accuracy=50.0  # type: AInitialAccuracy
                 ):
        # type: (...) -> None
        super(ExposureDeadtimePart, self).__init__(name)
        self.readout_time = NumberMeta(
            "float64", readout_desc,
            tags=[Widget.TEXTINPUT.tag(), config_tag()]
        ).create_attribute_model(initial_readout_time)
        self.frequency_accuracy = NumberMeta(
            "float64", frequency_accuracy_desc,
            tags=[Widget.TEXTINPUT.tag(), config_tag()]
        ).create_attribute_model(initial_frequency_accuracy)
        # Hooks
        self.register_hooked(
            scanning.hooks.ReportStatusHook, self.report_status)
        self.register_hooked(
            scanning.hooks.ValidateHook, self.validate)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(ExposureDeadtimePart, self).setup(registrar)
        # Attributes
        registrar.add_attribute_model(
            "readoutTime", self.readout_time, self.readout_time.set_value)
        registrar.add_attribute_model(
            "frequencyAccuracy", self.frequency_accuracy,
            self.frequency_accuracy.set_value)

    @add_call_types
    def validate(self, generator):
        # type: (scanning.hooks.AGenerator) -> None
        info = ExposureDeadtimeInfo(
            self.readout_time.value, self.frequency_accuracy.value)
        assert generator.duration > 0, \
            "Duration %s for generator must be >0 to signify constant " \
            "exposure" % (generator.duration,)
        info.calculate_exposure(generator.duration)

    @add_call_types
    def report_status(self):
        # type: () -> scanning.hooks.UInfos
        info = ExposureDeadtimeInfo(
            self.readout_time.value, self.frequency_accuracy.value)
        return info
