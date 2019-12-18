from annotypes import Anno, add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin, scanning

APartName = builtin.parts.APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility

with Anno("The demand value to move the axis to"):
    ADemand = float


@builtin.util.no_save("demand")
class MotorPreMovePart(builtin.parts.ChildPart):

    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 demand,  # type: ADemand
                 initial_visibility=False  # type: AInitialVisibility
                 ):
        # type: (...) -> None
        super(MotorPreMovePart,
              self).__init__(name,
                             mri,
                             stateful=False,
                             initial_visibility=initial_visibility)
        self.demand = demand

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(MotorPreMovePart, self).setup(registrar)
        registrar.hook(scanning.hooks.ConfigureHook, self.on_configure)

    @add_call_types
    def on_configure(self, context):
        # type: (builtin.hooks.AContext) -> None
        childBlock = context.block_view(self.mri)
        childBlock.demand.put_value(self.demand)
