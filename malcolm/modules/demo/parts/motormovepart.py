import time

from annotypes import Anno, add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri

with Anno("The demand value to move our counter motor to"):
    ADemand = float
with Anno("The amount of time to get to the demand position"):
    ADuration = float


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
    def move(self, context, demand, duration=0):
        # type: (builtin.hooks.AContext, ADemand, ADuration) -> None
        """Move the motor to the demand value, taking duration seconds"""
        child = context.block_view(self.mri)
        if duration > 0:
            # Given a time, go at that rate
            velocity = abs(demand - child.readback.value) / duration
        else:
            # Go as fast as possible
            velocity = 1000000
        # First set acceleration time and velocity
        child.put_attribute_values(dict(
            accelerationTime=0,
            velocity=velocity,
        ))
        # Then the demand to do the move
        child.demand.put_value(demand)
