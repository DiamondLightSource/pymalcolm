from annotypes import add_call_types

from malcolm.modules import builtin, scanning
from ..infos import ControllerInfo


class BrickPart(builtin.parts.ChildPart):
    def __init__(self, name, mri):
        # type: (builtin.parts.APartName, builtin.parts.AMri) -> None
        super(BrickPart, self).__init__(name, mri, initial_visibility=True)
        # Hooks
        self.register_hooked(scanning.hooks.ReportStatusHook,
                             self.report_status)

    @add_call_types
    def report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        controller_info = ControllerInfo(child.i10.value)
        return controller_info

