from annotypes import add_call_types

from malcolm.core import Hook
from malcolm.modules import builtin, scanning
from ..infos import MotorInfo


class RawMotorPart(builtin.parts.ChildPart):
    def on_hook(self, hook):
        # type: (Hook) -> None
        if isinstance(Hook, scanning.hooks.ReportStatusHook):
            hook(self.report_status)

    @add_call_types
    def report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.params.mri)
        max_velocity = child.maxVelocity.value
        acceleration = float(max_velocity) / child.accelerationTime.value
        motor_info = MotorInfo(
            cs_axis=child.csAxis.value,
            cs_port=child.csPort.value,
            acceleration=acceleration,
            resolution=child.resolution.value,
            offset=child.offset.value,
            max_velocity=max_velocity,
            current_position=child.readback.value,
            scannable=child.scannable.value,
            velocity_settle=child.velocitySettle.value
        )
        return motor_info
