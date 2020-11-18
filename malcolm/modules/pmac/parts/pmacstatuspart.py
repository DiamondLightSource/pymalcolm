from annotypes import Anno, add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin, scanning

from ..infos import PmacVariablesInfo

with Anno("The Servo Frequency of the PMAC in Hz"):
    AServoFrequency = float


class PmacStatusPart(builtin.parts.ChildPart):
    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Add methods
        registrar.add_method_model(
            self.servo_frequency, "servoFrequency", needs_context=True
        )
        # Hooks
        registrar.hook(scanning.hooks.ReportStatusHook, self.report_status)

    @add_call_types
    def servo_frequency(self, context: builtin.hooks.AContext) -> AServoFrequency:
        child = context.block_view(self.mri)
        freq = 8388608000.0 / child.i10.value
        return freq

    @add_call_types
    def report_status(self, context: scanning.hooks.AContext) -> scanning.hooks.UInfos:
        child = context.block_view(self.mri)
        info = PmacVariablesInfo(
            child.iVariables.value, child.pVariables.value, child.mVariables.value
        )
        return info
