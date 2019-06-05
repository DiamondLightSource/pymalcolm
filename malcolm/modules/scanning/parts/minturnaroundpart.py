from annotypes import Anno, add_call_types

from malcolm.core import Part, Widget, config_tag, PartRegistrar, APartName, \
    NumberMeta, Display
from ..hooks import ReportStatusHook, UInfos
from ..infos import MinTurnaroundInfo

with Anno("Initial value for min time between non-joined points"):
    AMinTurnaround = float


class MinTurnaroundPart(Part):
    def __init__(self, name="minTurnaround", value=None):
        # type: (APartName, AMinTurnaround) -> None
        super(MinTurnaroundPart, self).__init__(name)
        self.attr = NumberMeta(
            "float64", "Minimum time for any gaps between non-joined points",
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
            display=Display(precision=6, units="s")
        ).create_attribute_model(value)

    @add_call_types
    def report_status(self):
        # type: () -> UInfos
        return MinTurnaroundInfo(self.attr.value)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(
            "minTurnaround", self.attr, self.attr.set_value)
        # Hooks
        registrar.hook(ReportStatusHook, self.report_status)
