from malcolm.controllers.builtin.runnablecontroller import RunnableController
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.parts.pmac.pmactrajectorypart import MotorInfo


class RawMotorPart(ChildPart):
    @RunnableController.ReportStatus
    def report_cs_info(self, _):
        acceleration = float(
            self.child.maxVelocity) / self.child.accelerationTime
        motor_info = MotorInfo(
            cs_axis=self.child.csAxis,
            cs_port=self.child.csPort,
            acceleration=acceleration,
            resolution=self.child.resolution,
            offset=self.child.offset,
            max_velocity=self.child.maxVelocity,
            current_position=self.child.position,
            scannable=self.child.scannable,
            velocity_settle=self.child.velocitySettle
        )
        return [motor_info]
