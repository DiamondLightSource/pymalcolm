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
        self.register_hooked(scanning.hooks.PauseHook,
                             self.resync)

    @add_call_types
    def report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        outputs = child.generalPurposeOutputs.value
        # Turn the uint16 into a 16 element bool array
        outputs_list = [(outputs >> i) & 1 for i in range(16)]
        controller_info = ControllerInfo(child.i10.value, outputs_list)
        return controller_info

    @add_call_types
    def reset(self, context):
        # type: (builtin.hooks.AContext) -> None
        super(BrickPart, self).reset(context)
        self.resync(context)

    @add_call_types
    def resync(self, context):
        # type: (scanning.hooks.AContext) -> None
        # The GPIO is polled in the medium loop, so force a poll now so that
        # report status is accurate, but report status needs to be quick so
        # can't do it there
        child = context.block_view(self.mri)
        child.pollAllNow()
