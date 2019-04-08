from annotypes import add_call_types, Anno

from malcolm.core import PartRegistrar
from malcolm.modules import builtin


with Anno("The Servo Frequency of the PMAC in Hz"):
    AServoFrequency = float


class PmacStatusPart(builtin.parts.ChildPart):
    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PmacStatusPart, self).setup(registrar)
        # Add methods
        registrar.add_method_model(
            self.servo_frequency, "servoFrequency", needs_context=True)

    @add_call_types
    def servo_frequency(self, context):
        # type: (builtin.hooks.AContext) -> AServoFrequency
        child = context.block_view(self.mri)
        freq = 8388608000. / child.i10.value
        return freq

