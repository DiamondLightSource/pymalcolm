# Treat all division as float division even in python2
from __future__ import division

from annotypes import add_call_types

from malcolm.modules import builtin, scanning
from malcolm.modules.builtin.parts import ChildPart
from ..infos import CSInfo


class CSPart(ChildPart):
    def __init__(self,
                 name,  # type: builtin.parts.APartName
                 mri,  # type: builtin.parts.AMri
                 ):
        # type: (...) -> None
        super(CSPart, self).__init__(name, mri, initial_visibility=True)
        # Hooks
        self.register_hooked(scanning.hooks.ReportStatusHook,
                             self.report_status)

    @add_call_types
    def report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        motor_info = CSInfo(self.mri, child.port.value)
        return motor_info
