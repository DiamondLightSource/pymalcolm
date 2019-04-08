from annotypes import Anno, add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri

with Anno("The demand value to move our counter motor to"):
    ADemand = float


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save("counter")
class MotorMovePart(builtin.parts.ChildPart):
    """Provides control of a `counter_block` within a `ManagerController`"""

    def __init__(self, name, mri):
        # type: (APartName, AMri) -> None
        super(MotorMovePart, self).__init__(
            name, mri, stateful=False, initial_visibility=True)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(MotorMovePart, self).setup(registrar)
        # Method
        registrar.add_method_model(
            self.move, self.name + "Move", needs_context=True)

    @add_call_types
    def move(self, context, demand):
        # type: (builtin.hooks.AContext, ADemand) -> None
        """Move the motor instantly to the demand value"""
        child = context.block_view(self.mri)
        # "Move" the motor
        child.counter.put_value(demand)
