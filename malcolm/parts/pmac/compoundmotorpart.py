from malcolm.controllers.scanning.runnablecontroller import RunnableController
from malcolm.parts.builtin import StatefulChildPart
from malcolm.parts.pmac.pmactrajectorypart import cs_axis_names
from malcolm.infos.pmac.motorinfo import MotorInfo


class CompoundMotorPart(StatefulChildPart):
    @RunnableController.ReportStatus
    def report_cs_info(self, context):
        child = context.block_view(self.params.mri)
        acceleration = float(
            child.maxVelocity) / child.accelerationTime
        # Split "@asyn(PORT,num)" into ["PORT", "num"]
        split = child.outLink.split("(")[1].rstrip(")").split(",")
        cs_port = split[0].strip()
        cs_axis = cs_axis_names[int(split[1].strip())-1]

        motor_info = MotorInfo(
            cs_axis=cs_axis,
            cs_port=cs_port,
            acceleration=acceleration,
            resolution=1.0,
            offset=child.offset,
            max_velocity=child.maxVelocity,
            current_position=child.position,
            scannable=child.scannable,
            velocity_settle=child.velocitySettle
        )
        return [motor_info]
