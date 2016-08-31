import time

from malcolm.core import method_takes, REQUIRED, Attribute, Part
from malcolm.core.vmetas import StringArrayMeta, NumberArrayMeta, NumberMeta
from malcolm.controllers.pmac.pmactrajectorycontroller import \
    PMACTrajectoryController, profile_table, cs_axis_names


@method_takes()
class DummyTrajectoryPart(Part):
    profile = None
    use = None
    axis_rbv = None

    def create_attributes(self):
        self.axis_rbv = {}
        for cs_axis in cs_axis_names:
            self.axis_rbv[cs_axis] = Attribute(NumberMeta(
                "float64", "%s readback value" % cs_axis), 0.0)
            yield (cs_axis, self.axis_rbv[cs_axis], None)

    @PMACTrajectoryController.BuildProfile
    @method_takes(
        "profile", profile_table, REQUIRED,
        "use", StringArrayMeta("List of profiles to send"), REQUIRED,
        "resolutions", NumberArrayMeta(
            "float64", "Resolutions for used axes"), REQUIRED,
        "offsets", NumberArrayMeta(
            "float64", "Offsets for used axes"), REQUIRED)
    def build_profile(self, _, params):
        self.profile = params.profile
        self.use = params.use

    @PMACTrajectoryController.RunProfile
    def execute_profile(self, _):
        for i, t in enumerate(self.profile.time):
            time.sleep(t)
            for cs_axis in self.use:
                self.axis_rbv[cs_axis].set_value(self.profile[cs_axis][i])
