from annotypes import add_call_types, Anno

from malcolm.core import APartName
from malcolm.modules import builtin, scanning
from ..infos import MotorInfo


with Anno("Whether the underlying motor is compound motor or not"):
    ACompound = bool


class MotorPart(builtin.parts.ChildPart):
    def __init__(self, name, mri, compound=False):
        # type: (APartName, builtin.parts.AMri, ACompound) -> None
        super(MotorPart, self).__init__(name, mri, initial_visibility=True)
        self.compound = compound
        # Hooks
        self.register_hooked(scanning.hooks.ReportStatusHook,
                             self.report_status)

    @add_call_types
    def report_status(self, context):
        # type: (scanning.hooks.AContext) -> scanning.hooks.UInfos
        child = context.block_view(self.mri)
        max_velocity = child.maxVelocity.value
        acceleration = float(max_velocity) / child.accelerationTime.value
        cs = child.cs.value
        if cs:
            cs_port, cs_axis = child.cs.value.split(",", 1)
        else:
            cs_port, cs_axis = "", ""
        if self.compound:
            resolution = 1.0
        else:
            resolution = child.resolution.value
        motor_info = MotorInfo(
            cs_axis=cs_axis,
            cs_port=cs_port,
            acceleration=acceleration,
            resolution=resolution,
            offset=child.offset.value,
            max_velocity=max_velocity,
            current_position=child.readback.value,
            scannable=self.name,
            velocity_settle=child.velocitySettle.value,
            units=child.units.value
        )
        return motor_info
