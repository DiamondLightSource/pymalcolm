from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.parts.pmac.pmactrajectorypart import MotorInfo


class RawMotorPart(LayoutPart):
    @RunnableController.Report
    def report_cs_info(self, _):
        motor_info = MotorInfo(
            cs_axis=self.child.cs_axis,
            cs_port=self.child.cs_port,
            acceleration_time=self.child.acceleration_time,
            resolution=self.child.resolution,
            offset=self.child.offset,
            max_velocity=self.child.max_velocity,
            current_position=self.child.position)
        return motor_info
