from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import PointGeneratorMeta, NumberMeta
from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.hdfwriterpart import DatasetSourceInfo


class DetectorDriverPart(LayoutPart):
    # Attributes
    readoutTime = None

    def create_attributes(self):
        for data in super(DetectorDriverPart, self).create_attributes():
            yield data
        self.readoutTime = NumberMeta(
            "float64", "Time taken to readout detector").make_attribute(0.002)
        yield "readoutTime", self.readoutTime, self.readoutTime.set_value

    @RunnableController.PreConfigure
    def report_info(self, _):
        return [DatasetSourceInfo("detector", "primary")]

    @RunnableController.Configuring
    @method_takes(
        "generator", PointGeneratorMeta("Generator instance"), REQUIRED)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        durations = set()
        for i in range(completed_steps, completed_steps + steps_to_do):
            point = params.generator.get_point(i)
            durations.add(point.duration)
        assert len(durations) == 1, \
            "Expected a fixed duration time, got %s" % list(durations)
        exposure = durations.pop()
        assert exposure is not None, \
            "Expected duration to be specified, got None"
        exposure -= self.readoutTime.value
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
