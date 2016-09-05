import time

from malcolm.core import method_takes, REQUIRED, Attribute, Part
from malcolm.core.vmetas import StringArrayMeta, NumberArrayMeta, NumberMeta, \
    BooleanMeta
from malcolm.controllers.pmac.pmactrajectorycontroller import \
    PMACTrajectoryController, profile_table, cs_axis_names


@method_takes()
class DummyTrajectoryPart(Part):
    profile = None
    use = None
    axis_rbv = None
    currentStep = None

    def create_attributes(self):
        self.axis_rbv = {}
        for cs_axis in cs_axis_names:
            self.axis_rbv[cs_axis] = Attribute(NumberMeta(
                "float64", "%s readback value" % cs_axis), 0.0)
            yield (cs_axis, self.axis_rbv[cs_axis], None)
        self.currentStep = Attribute(NumberMeta(
            "int32", "Readback of number of scan steps"), 0)
        yield "currentStep", self.currentStep, None

    @PMACTrajectoryController.BuildProfile
    @method_takes(
        "profile", profile_table, REQUIRED,
        "use", StringArrayMeta("List of profiles to send"), REQUIRED,
        "resolutions", NumberArrayMeta(
            "float64", "Resolutions for used axes"), REQUIRED,
        "offsets", NumberArrayMeta(
            "float64", "Offsets for used axes"), REQUIRED,
        "reset_current_step", BooleanMeta("Reset currentStep attr"), True)
    def build_profile(self, _, params):
        if params.reset_current_step:
            self.currentStep.set_value(0)
        self.profile = params.profile
        self.use = params.use

    @PMACTrajectoryController.RunProfile
    @method_takes(
        "current_steps", NumberArrayMeta(
            "int32", "Value of currentStep for each line scanned"), [])
    def execute_profile(self, task, params):
        for i, t in enumerate(self.profile.time):
            task.sleep(t)
            for cs_axis in self.use:
                self.axis_rbv[cs_axis].set_value(self.profile[cs_axis][i])
            if len(params.current_steps) > 0:
                current_step = params.current_steps[i]
                if current_step != self.currentStep.value:
                    self.currentStep.set_value(current_step)
