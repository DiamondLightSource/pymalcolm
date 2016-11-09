from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.parts.pmac.pmactrajectorypart import MotorInfo, cs_axis_names


class CompoundMotorPart(ChildPart):
    @RunnableController.PreConfigure
    def report_cs_info(self, _):
        # Split "@asyn(PORT,num)" into ["PORT", "num"]
        split = self.child.outLink.split("(")[1].rstrip(")").split(",")
        cs_port = split[0].strip()
        cs_axis = cs_axis_names[int(split[1].strip())-1]

        motor_info = MotorInfo(
            cs_axis=cs_axis,
            cs_port=cs_port,
            acceleration_time=self.child.accelerationTime,
            resolution=1.0,
            offset=self.child.offset,
            max_velocity=self.child.maxVelocity,
            current_position=self.child.position,
            scannable=self.child.scannable
        )
        return motor_info
