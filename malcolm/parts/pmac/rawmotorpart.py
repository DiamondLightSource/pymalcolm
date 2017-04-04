from malcolm.controllers.scanning.runnablecontroller import RunnableController
from malcolm.parts.builtin import StatefulChildPart
from malcolm.infos.pmac.motorinfo import MotorInfo


class RawMotorPart(StatefulChildPart):
    @RunnableController.ReportStatus
    def report_cs_info(self, context):
        child = context.block_view(self.params.mri)
        acceleration = float(
            child.maxVelocity) / child.accelerationTime
        motor_info = MotorInfo(
            cs_axis=child.csAxis,
            cs_port=child.csPort,
            acceleration=acceleration,
            resolution=child.resolution,
            offset=child.offset,
            max_velocity=child.maxVelocity,
            current_position=child.position,
            scannable=child.scannable,
            velocity_settle=child.velocitySettle
        )
        return [motor_info]
