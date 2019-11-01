from annotypes import Anno, add_call_types

from malcolm.core import PartRegistrar
from .. import hooks
from malcolm.modules.builtin.hooks import AContext
from malcolm.modules import builtin

with Anno("Open position of shutter"):
    AOpenVal = str

with Anno("Closed position of shutter"):
    AClosedVal = str

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


class ShutterPart(builtin.parts.ChildPart):
    """Part for controlling a shutter via a CAChoicePart"""

    def __init__(self, name, mri, open_value, closed_value):
        # type: (APartName, AMri, AOpenVal, AClosedVal) -> None
        super(ShutterPart, self).__init__(name, mri, initial_visibility=True)
        self.open_value = open_value
        self.closed_value = closed_value

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(ShutterPart, self).setup(registrar)
        # Hooks
        registrar.hook(hooks.PreRunHook, self.open_shutter)
        registrar.hook((
            hooks.PauseHook, hooks.AbortHook, hooks.PostRunReadyHook), self.close_shutter)

    @add_call_types
    def open_shutter(self, context):
        # type: (AContext) -> None
        child = context.block_view(self.mri)
        child.shutter.put_value(self.open_value)

    @add_call_types
    def close_shutter(self, context):
        # type: (AContext) -> None
        child = context.block_view(self.mri)
        child.shutter.put_value(self.closed_value)
