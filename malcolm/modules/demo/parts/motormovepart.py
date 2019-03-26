import time

from annotypes import Anno, add_call_types

from malcolm.core import Context, PartRegistrar
from malcolm.modules import builtin

with Anno("The demand value to move our counter motor to"):
    ADemand = float


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save("counter")
class MotorMovePart(builtin.parts.ChildPart):
    """Provides control of a `counter_block` within a `ManagerController`"""
    # A context that we can use for controlling the counter
    context = None  # type: Context

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(MotorMovePart, self).setup(registrar)
        # Method
        registrar.add_method_model(self.move, self.name + "Move")

    @add_call_types
    def init(self, context):
        # type: (builtin.hooks.AContext) -> None
        # Store the context for later use
        self.context = context
        super(MotorMovePart, self).init(context)

    @add_call_types
    def move(self, demand):
        # type: (ADemand) -> None
        child = self.context.block_view(self.mri)
        # "Move" the motor
        child.counter.put_value(demand)
