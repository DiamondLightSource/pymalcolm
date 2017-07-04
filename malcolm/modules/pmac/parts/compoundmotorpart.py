from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.builtin.parts import StatefulChildPart
from malcolm.modules.pmac.infos import MotorInfo
from .pmactrajectorypart import cs_axis_names


class CompoundMotorPart(StatefulChildPart):
    @RunnableController.ReportStatus
    def report_cs_info(self, context):
        child = context.block_view(self.params.mri)
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
        return [motor_info]
