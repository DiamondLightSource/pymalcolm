from malcolm.controllers.scanning.runnablecontroller import RunnableController
from malcolm.parts.builtin import StatefulChildPart
from malcolm.infos.pmac.motorinfo import MotorInfo


class RawMotorPart(StatefulChildPart):
    @RunnableController.ReportStatus
    def report_cs_info(self, context):
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
            current_position=child.position.value,
            scannable=child.scannable.value,
            velocity_settle=child.velocitySettle.value
        )
        return [motor_info]
