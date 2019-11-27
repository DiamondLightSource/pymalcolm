from annotypes import Anno, add_call_types

from malcolm.core import Part, Widget, config_tag, PartRegistrar, APartName, \
    NumberMeta, Display
from ..hooks import ReportStatusHook, UInfos
from ..infos import MinTurnaroundInfo

with Anno("Initial value for min time between non-joined points"):
    AMinTurnaround = float
with Anno("Minimum interval between turnaround points"):
    ATurnaroundInterval = float


class MinTurnaroundPart(Part):
    def __init__(self, name="minTurnaround", gap=None, interval=None):
        # type: (APartName, AMinTurnaround, ATurnaroundInterval) -> None
        super(MinTurnaroundPart, self).__init__(name)
        self.gap = NumberMeta(
            "float64", "Minimum time for any gaps between non-joined points",
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
            display=Display(precision=6, units="s")
        ).create_attribute_model(gap)
        self.interval = NumberMeta(
            "float64", "Minimum interval between turnaround points",
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
            display=Display(precision=6, units="s")
        ).create_attribute_model(interval)

    @add_call_types
    def on_report_status(self):
        # type: () -> UInfos
        return MinTurnaroundInfo(self.gap.value, self.interval.value)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(
            "minTurnaround", self.gap, self.gap.set_value)
        registrar.add_attribute_model(
            "minTurnaroundInterval", self.interval, self.interval.set_value)
        # Hooks
        registrar.hook(ReportStatusHook, self.on_report_status)
