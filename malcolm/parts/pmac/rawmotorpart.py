from malcolm.controllers.managercontroller import ManagerController
from malcolm.core import method_returns, REQUIRED
from malcolm.core.vmetas import StringMeta, NumberMeta
from malcolm.parts.builtin.layoutpart import LayoutPart


class RawMotorPart(LayoutPart):

    @ManagerController.Report
    @method_returns(
        "cs_axis", StringMeta("CS axis (like A, B, I, 0)"), REQUIRED,
        "cs_port", StringMeta("CS port name"), REQUIRED,
        "acceleration_time", NumberMeta(
            "float64", "Seconds to velocity"), REQUIRED,
        "resolution", NumberMeta(
            "float64", "Motor resolution"), REQUIRED,
        "offset", NumberMeta(
            "float64", "Motor user offset"), REQUIRED,
        "max_velocity", NumberMeta(
            "float64", "Maximum motor velocity"), REQUIRED,
        "current_position", NumberMeta(
            "float64", "Current motor position"), REQUIRED)
    def report_cs_info(self, _, returns):
        returns.cs_axis = self.child.cs_axis
        returns.cs_port = self.child.cs_port
        returns.acceleration_time = self.child.acceleration_time
        returns.resolution = self.child.resolution
        returns.offset = self.child.offset
        returns.max_velocity = self.child.max_velocity
        returns.current_position = self.child.position
        return returns
