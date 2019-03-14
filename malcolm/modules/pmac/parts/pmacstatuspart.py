from annotypes import add_call_types, Anno

from malcolm.core import PartRegistrar
from malcolm.modules import builtin


with Anno("The Servo Frequency of the PMAC in Hz"):
    AServoFrequency = float


class PmacStatusPart(builtin.parts.ChildPart):
    # The context we will use for all our functions
    context = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PmacStatusPart, self).setup(registrar)
        # Add methods
        registrar.add_method_model(self.servo_frequency, "servoFrequency")

    @add_call_types
    def init(self, context):
        # type: (builtin.hooks.AContext) -> None
        # Store the context for later use
        self.context = context
        super(PmacStatusPart, self).init(context)

    @add_call_types
    def servo_frequency(self):
        # type: () -> AServoFrequency
        child = self.context.block_view(self.mri)
        freq = 8388608000. / child.i10.value
        return freq

