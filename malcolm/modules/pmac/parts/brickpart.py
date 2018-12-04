from annotypes import add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin, scanning
from ..infos import ControllerInfo


class BrickPart(builtin.parts.ChildPart):
    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(BrickPart, self).setup(registrar)
        # Hooks
        self.register_hooked(scanning.hooks.ReportStatusHook,
                             self.report_status)

    @add_call_types
    def report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        controller_info = ControllerInfo(child.i10.value)
        return controller_info

