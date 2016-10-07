from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import PointGeneratorMeta
from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.runnablecontroller import RunnableController


class DetectorDriverPart(LayoutPart):
    @RunnableController.Configuring
    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        exposures = set()
        for i in range(completed_steps, completed_steps + steps_to_do):
            point = params.generator.get_point(i)
            exposures.add(point.duration)
        assert len(exposures) == 1, \
            "Expected a fixed duration time, got %s" % list(exposures)
        exposure = exposures.pop()
        assert exposure is not None, \
            "Expected duration to be specified, got None"
        task.put({
            self.child["exposure"]: exposure,
            self.child["imageMode"]: "Multiple",
            self.child["numImages"]: steps_to_do,
            self.child["arrayCounter"]: completed_steps,
            self.child["arrayCallbacks"]: True,
        })

    @RunnableController.Running
    def run(self, task, _):
        task.post(self.child["start"])

    @RunnableController.Aborting
    def abort(self, task):
        task.post(self.child["stop"])
