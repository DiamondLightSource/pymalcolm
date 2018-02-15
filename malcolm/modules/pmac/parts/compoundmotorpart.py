from annotypes import add_call_types

from malcolm.modules import builtin, scanning
from ..infos import MotorInfo
from .pmactrajectorypart import cs_axis_names


class CompoundMotorPart(builtin.parts.ChildPart):
    def on_hook(self, hook):
        if isinstance(hook, scanning.hooks.ReportStatusHook):
            hook(self.report_status)

    @add_call_types
    def report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        max_velocity = child.maxVelocity.value
        acceleration = float(max_velocity) / child.accelerationTime.value

        # Split "@asyn(PORT,num)" into ["PORT", "num"]
        split = child.outLink.value.split("(")[1].rstrip(")").split(",")
        cs_port = split[0].strip()
        cs_axis = cs_axis_names[int(split[1].strip())-1]

        motor_info = MotorInfo(
            cs_axis=cs_axis,
            cs_port=cs_port,
            acceleration=acceleration,
            resolution=1.0,
            offset=child.offset.value,
            max_velocity=max_velocity,
            current_position=child.readback.value,
            scannable=child.scannable.value,
            velocity_settle=child.velocitySettle.value
        )
        return motor_info
