from malcolm.core import method_takes, REQUIRED, Attribute
from malcolm.core.vmetas import StringArrayMeta, NumberArrayMeta, NumberMeta
from malcolm.controllers.pmac.pmactrajectorycontroller import \
    PMACTrajectoryController, profile_table, cs_axis_names
from malcolm.parts.builtin.layoutpart import LayoutPart

# Number of seconds that a trajectory tick is
TICK_S = 0.00025


class PMACTrajectoryPart(LayoutPart):
    completedSteps = None

    def create_attributes(self):
        self.completedSteps = Attribute(NumberMeta(
            "int32", "Readback of number of scan steps"), 0)
        yield "completedSteps", self.completedSteps, None

    @PMACTrajectoryController.BuildProfile
    @method_takes(
        "profile", profile_table, REQUIRED,
        "use", StringArrayMeta("List of profiles to send"), REQUIRED,
        "resolutions", NumberArrayMeta(
            "float64", "Resolutions for used axes"), REQUIRED,
        "offsets", NumberArrayMeta(
            "float64", "Offsets for used axes"), REQUIRED)
    def build_profile(self, task, params):
        # First set the resolutions and offsets
        attr_dict = dict()
        for i, cs_axis in enumerate(params.use):
            assert cs_axis in cs_axis_names, \
                "CS axis %s is not in %s" % (cs_axis, cs_axis_names)
            attr_dict["resolution%s" % cs_axis] = params.resolutions[i]
            attr_dict["offset%s" % cs_axis] = params.offsets[i]
        task.put({self.child[k]: v for k, v in attr_dict.items()})

        # work out the time for each point in PMAC ticks
        time_array = []
        overflow = 0
        for t in params.profile.time:
            ticks = t / TICK_S
            overflow += (ticks % 1)
            ticks = int(ticks)
            if overflow > 1:
                overflow -= 1
                ticks += 1
            time_array.append(ticks)

        # Now set the arrays
        attr_dict = dict(
            time_array=time_array,
            velocity_mode=params.profile.velocity_mode,
            num_points=len(time_array)
        )
        for cs_axis in cs_axis_names:
            attr_dict["use%s" % cs_axis] = cs_axis in params.use
        for cs_axis in params.use:
            attr_dict["positions%s" % cs_axis] = params.profile[cs_axis]
        task.put({self.child[k]: v for k, v in attr_dict.items()})
        task.post(self.child["build_profile"])

    def update_step(self, scanned, completed_steps):
        if len(completed_steps) > 0:
            completed_steps = completed_steps[scanned - 1]
            if completed_steps != self.completedSteps.value:
                self.completedSteps.set_value(completed_steps)

    @PMACTrajectoryController.RunProfile
    @method_takes(
        "completed_steps", NumberArrayMeta(
            "int32", "Value of completedSteps for each line scanned"), [])
    def execute_profile(self, task, params):
        task.subscribe(self.child["points_scanned"], self.update_step,
                       params.completed_steps)
        task.post(self.child["execute_profile"])

    @PMACTrajectoryController.Aborting
    def stop_execution(self, task):
        task.post(self.child["abort_profile"])
