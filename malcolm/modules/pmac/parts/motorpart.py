from annotypes import add_call_types

from malcolm.core import APartName
from malcolm.modules import builtin, scanning
from ..infos import MotorInfo


class MotorPart(builtin.parts.ChildPart):
    def __init__(self, name, mri):
        # type: (APartName, builtin.parts.AMri) -> None
        super(MotorPart, self).__init__(name, mri, initial_visibility=True)
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
        motor_info = MotorInfo(
            cs_axis=cs_axis,
            cs_port=cs_port,
            acceleration=acceleration,
            resolution=child.resolution.value,
            offset=child.offset.value,
            max_velocity=max_velocity,
            current_position=child.readback.value,
            # We put a scannable in the object rather than relying on the part
            # name of the dictionary as it allows the part_info structure to be
            # flattened and iterated over in PmacTrajectoryPart
            scannable=self.name,
            velocity_settle=child.velocitySettle.value,
            units=child.units.value
        )
        return motor_info
