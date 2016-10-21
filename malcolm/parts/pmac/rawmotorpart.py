from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.builtin.layoutpart import ChildPart
from malcolm.parts.pmac.pmactrajectorypart import MotorInfo


class RawMotorPart(ChildPart):
    @RunnableController.ReportStatus
    def report_cs_info(self, _):
        motor_info = MotorInfo(
            cs_axis=self.child.csAxis,
            cs_port=self.child.csPort,
            acceleration_time=self.child.accelerationTime,
            resolution=self.child.resolution,
            offset=self.child.offset,
            max_velocity=self.child.maxVelocity,
            current_position=self.child.position,
            scannable=self.child.scannable
        )
        return motor_info
