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

# How long between ticks of the "motor" position while moving
UPDATE_TICK = 0.1


# We will set these attributes on the child block, so don't save them
@builtin.util.no_save("counter")
class CounterMovePart(builtin.parts.ChildPart):
    """Provides control of a `counter_block` within a `ManagerController`"""

    def __init__(self, name: APartName, mri: AMri) -> None:
        super().__init__(name, mri, stateful=False, initial_visibility=True)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Method
        registrar.add_method_model(self.move, self.name + "Move", needs_context=True)

    @add_call_types
    def move(
        self, context: builtin.hooks.AContext, demand: ADemand, duration: ADuration = 0
    ) -> None:
        """Move the counter to the demand value, taking duration seconds like
        a motor would do"""
        start = time.time()
        child = context.block_view(self.mri)
        distance = demand - child.counter.value
        remaining = duration
        # "Move" the motor, ticking at UPDATE_TICK rate
        while remaining > 0:
            child.counter.put_value(demand - distance * remaining / duration)
            context.sleep(min(remaining, UPDATE_TICK))
            remaining = start + duration - time.time()
        # Final move to make sure we end up at the right place
        child.counter.put_value(demand)
