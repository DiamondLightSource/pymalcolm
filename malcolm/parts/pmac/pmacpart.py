from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import StringArrayMeta, NumberArrayMeta
from malcolm.controllers.pmac.pmactrajectorycontroller import \
    PMACTrajectoryController, profile_table, cs_axis_names
from malcolm.parts.builtin.layoutpart import LayoutPart

# Number of seconds that a trajectory tick is
TICK_S = 0.00025


class PmacPart(LayoutPart):
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
            attr_dict["offsets%s" % cs_axis] = params.offsets[i]
        task.put({self.child[k]: v for k, v in attr_dict.items()})

        # work out the time for each point in PMAC ticks
        times = []
        overflow = 0
        for t in params.profile.time:
            ticks = t / TICK_S
            overflow += (ticks % 1)
            ticks = int(ticks)
            if overflow > 1:
                overflow -= 1
                ticks += 1
            times.append(ticks)

        # Now set the arrays
        attr_dict = dict(
            times=times,
            velocity_mode=params.profile.velocity_mode)
        for cs_axis in cs_axis_names:
            attr_dict["use%s" % cs_axis] = cs_axis in params.use
        for cs_axis in params.use:
            attr_dict["positions%s" % cs_axis] = params.profile[cs_axis]
        task.put({self.child[k]: v for k, v in attr_dict.items()})
        task.post(self.child["build_profile"])

    @PMACTrajectoryController.RunProfile
    def execute_profile(self, task):
        task.post(self.child["execute_profile"])
