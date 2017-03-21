from malcolm.core import method_also_takes, REQUIRED, method_takes
from malcolm.core.vmetas import PointGeneratorMeta, NumberMeta, ChoiceMeta
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.hdfwriterpart import NDArrayDatasetInfo


# Args for configure() and validate
configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED]


@method_also_takes(
    "readoutTime", NumberMeta(
        "float64", "Default time taken to readout detector"), 8e-6)
class DetectorDriverPart(ChildPart):
    # Attributes
    readout_time = None
    trigger_mode = None

    # Store future for waiting for completion
    start_future = None

    def create_attributes(self):
        for data in super(DetectorDriverPart, self).create_attributes():
            yield data
        meta = NumberMeta("float64", "Time taken to readout detector")
        self.readout_time = meta.make_attribute(self.params.readoutTime)
        yield "readoutTime", self.readout_time, self.readout_time.set_value
        meta = ChoiceMeta("Whether detector is software or hardware triggered",
                          ["Software", "Hardware"])
        self.trigger_mode = meta.make_attribute("Hardware")
        yield "triggerMode", self.trigger_mode, None

    @RunnableController.Reset
    def reset(self, task):
        super(DetectorDriverPart, self).reset(task)
        self.abort(task)

    @RunnableController.ReportStatus
    def report_configuration(self, _):
        return [NDArrayDatasetInfo(name=self.name, rank=2)]

    @RunnableController.Validate
    @method_takes(*configure_args)
    def validate(self, task, part_info, params):
        exposure = params.generator.duration
        assert exposure > 0, \
            "Duration %s for generator must be >0 to signify constant exposure"\
            % exposure
        # TODO: should really get this from an Info from pmac trajectory part...
        exposure -= self.readout_time.value
        assert exposure > 0.0, \
            "Exposure time %s too small when readoutTime taken into account" % (
                exposure)

    @RunnableController.Configure
    @RunnableController.PostRunReady
    @RunnableController.Seek
    @method_takes(*configure_args)
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        task.unsubscribe_all()
        exposure = params.generator.duration - self.readout_time.value
        task.put_many(self.child, dict(
            exposure=exposure,
            imageMode="Multiple",
            numImages=steps_to_do,
            arrayCounter=completed_steps,
            arrayCallbacks=True))
        self.post_configure(task, params)

    def post_configure(self, task, params):
        if self.trigger_mode.value == "Hardware":
            # Start now
            self.start_future = task.post_async(self.child["start"])

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, task, update_completed_steps):
        task.subscribe(self.child["arrayCounter"], update_completed_steps, self)
        if self.trigger_mode.value != "Hardware":
            # Start now
            self.start_future = task.post_async(self.child["start"])
        task.wait_all(self.start_future)

    @RunnableController.Abort
    @RunnableController.Pause
    def abort(self, task):
        task.post(self.child["stop"])

