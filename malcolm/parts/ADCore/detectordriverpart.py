from malcolm.core import method_also_takes, REQUIRED, method_takes
from malcolm.core.vmetas import PointGeneratorMeta, NumberMeta
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.hdfwriterpart import DatasetSourceInfo


# Maximum number of points to check for fixed duration
MAX_CHECK = 5000

# Args for configure() and validate
configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED]

@method_also_takes(
    "readoutTime", NumberMeta(
        "float64", "Default time taken to readout detector"), 0.002)
class DetectorDriverPart(ChildPart):
    # Attributes
    readoutTime = None

    # Stored futures
    start_future = None

    def create_attributes(self):
        for data in super(DetectorDriverPart, self).create_attributes():
            yield data
        meta = NumberMeta("float64", "Time taken to readout detector")
        self.readoutTime = meta.make_attribute(self.params.readoutTime)
        yield "readoutTime", self.readoutTime, self.readoutTime.set_value

    @RunnableController.Reset
    def reset(self, task):
        super(DetectorDriverPart, self).reset(task)
        self.abort(task)

    @RunnableController.ReportStatus
    def report_configuration(self, _):
        return [DatasetSourceInfo("detector", "primary")]

    @RunnableController.Validate
    @method_takes(*configure_args)
    def validate(self, task, completed_steps, steps_to_do, part_info, params):
        durations = set()
        max_points = min(MAX_CHECK, completed_steps + steps_to_do)
        for i in range(completed_steps, max_points):
            point = params.generator.get_point(i)
            durations.add(point.duration)
        assert len(durations) == 1, \
            "Expected a fixed duration time, got %s" % list(durations)
        exposure = durations.pop()
        assert exposure is not None, \
            "Expected duration to be specified, got None"
        exposure -= self.readoutTime.value
        assert exposure > 0.0, \
            "Exposure time %s too small when readoutTime taken into account" % (
                exposure)
        return exposure

    @RunnableController.Configure
    @RunnableController.PostRunReady
    @RunnableController.Seek
    @method_takes(*configure_args)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        # Stop in case we are already running
        stop_future = task.post_async(self.child["stop"])
        exposure = self.validate(
            task, completed_steps, steps_to_do, part_info, params)
        task.wait_all(stop_future)
        task.put_many(self.child, dict(
            exposure=exposure,
            imageMode="Multiple",
            numImages=steps_to_do,
            arrayCounter=completed_steps,
            arrayCallbacks=True))
        self.start_future = task.post_async(self.child["start"])

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, task, update_completed_steps):
        task.subscribe(self.child["arrayCounter"], update_completed_steps, self)
        task.wait_all(self.start_future)

    @RunnableController.Abort
    @RunnableController.Pause
    def abort(self, task):
        task.post(self.child["stop"])

