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
    def __init__(
        self,
        name: APartName,
        mri: AMri,
        demand: ADemand,
        initial_visibility: AInitialVisibility = False,
    ) -> None:
        super().__init__(
            name, mri, stateful=False, initial_visibility=initial_visibility
        )
        self.demand = demand

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        registrar.hook(scanning.hooks.ConfigureHook, self.on_configure)

    @add_call_types
    def on_configure(self, context: builtin.hooks.AContext) -> None:
        childBlock = context.block_view(self.mri)
        childBlock.demand.put_value(self.demand)
