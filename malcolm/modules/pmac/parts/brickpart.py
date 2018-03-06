from annotypes import add_call_types

from malcolm.core import PartRegistrar
from malcolm.modules import builtin, scanning
from ..infos import ControllerInfo


class BrickPart(builtin.parts.ChildPart):
    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(BrickPart, self).setup(registrar)
        self.register_hooked(scanning.hooks.ReportStatusHook,
                             self.report_status)

    @add_call_types
    def report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        outputs = child.generalPurposeOutputs.value
        # Turn the uint16 into a 16 element bool array
        outputs_list = [bool((outputs >> i) & 1) for i in range(16)]
        controller_info = ControllerInfo(child.i10.value, outputs_list)
        return controller_info
