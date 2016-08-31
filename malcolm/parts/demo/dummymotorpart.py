from malcolm.core import method_takes, method_returns, REQUIRED, Part
from malcolm.core.vmetas import StringMeta
from malcolm.controllers.pmac import PMACTrajectoryController


@method_takes(
    "cs_axis", StringMeta("CS axis to return"), REQUIRED,
    "cs_port", StringMeta("CS port name to return"), "CS1",
)
class DummyMotorPart(Part):

    @PMACTrajectoryController.ReportCSInfo
    @method_returns(
        "cs_axis", StringMeta("CS axis (like A, B, I, 0)"), REQUIRED,
        "cs_port", StringMeta("CS port name"), REQUIRED)
    def report_cs_info(self, _, returns):
        returns.cs_axis = self.params.cs_axis
        returns.cs_port = self.params.cs_port
        return returns

    def get_move_time(self, demand, current=None):
        if current is None:
            current = demand
        max_velocity = 1.0
        time = abs(demand - current) / max_velocity
        return time

    def get_acceleration_time(self):
        return 0.1

    def get_resolution(self):
        return 0.001

    def get_offset(self):
        return 1000.0
