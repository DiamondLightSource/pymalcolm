from malcolm.core import method_returns, REQUIRED
from malcolm.core.vmetas import StringMeta
from malcolm.controllers.pmac import PMACTrajectoryController
from malcolm.parts.builtin.layoutpart import LayoutPart


class RawMotorPart(LayoutPart):

    @PMACTrajectoryController.MotorReportCSInfo
    @method_returns([
        "cs_axis", StringMeta("CS axis (like A, B, I, 0)"), REQUIRED,
        "cs_port", StringMeta("CS port name"), REQUIRED])
    def report_cs_info(self, _, returns):
        returns.cs_axis = self.child.cs_axis
        returns.cs_port = self.child.cs_port
        return returns

    def get_move_time(self, demand, current=None):
        if current is None:
            current = self.child.position
        time = abs(demand - current) / self.child.max_velocity
        return time

    def get_acceleration_time(self):
        return self.child.acceleration_time

    def get_resolution(self):
        return self.child.resolution

    def get_offset(self):
        return self.child.offset
