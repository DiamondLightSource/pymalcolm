from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.builtin.childpart import ChildPart
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
        return [motor_info]

    @RunnableController.Abort
    @RunnableController.Pause
    def abort(self, task):
        self.log_warning("Waiting for motor to stop moving")
        # Wait for the motor to stop moving
        task.when_matches(self.child["doneMoving"], 1)
