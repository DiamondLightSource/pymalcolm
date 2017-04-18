from malcolm.controllers.scanning.runnablecontroller import RunnableController
from malcolm.core import method_also_takes, REQUIRED, method_takes
from malcolm.infos.ADCore.ndarraydatasetinfo import NDArrayDatasetInfo
from malcolm.parts.builtin import StatefulChildPart
from malcolm.modules.builtin.vmetas import NumberMeta, ChoiceMeta
from malcolm.vmetas.scanpointgenerator import PointGeneratorMeta

# Args for configure() and validate
configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED]


@method_also_takes(
    "readoutTime", NumberMeta(
        "float64", "Default time taken to readout detector"), 7e-5)
class DetectorDriverPart(StatefulChildPart):
    # Attributes
    readout_time = None
    trigger_mode = None

    # Store future for waiting for completion
    start_future = None

    def create_attributes(self):
        for data in super(DetectorDriverPart, self).create_attributes():
            yield data
        meta = NumberMeta("float64", "Time taken to readout detector")
        self.readout_time = meta.create_attribute(self.params.readoutTime)
        yield "readoutTime", self.readout_time, self.readout_time.set_value
        meta = ChoiceMeta("Whether detector is software or hardware triggered",
                          ["Software", "Hardware"])
        self.trigger_mode = meta.create_attribute("Hardware")
        yield "triggerMode", self.trigger_mode, None

    @RunnableController.Reset
    def reset(self, context):
        super(DetectorDriverPart, self).reset(context)
        self.abort(context)

    @RunnableController.ReportStatus
    def report_configuration(self, _):
        return [NDArrayDatasetInfo(name=self.name, rank=2)]

    @RunnableController.Validate
    @method_takes(*configure_args)
    def validate(self, context, part_info, params):
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
    def configure(self, context, completed_steps, steps_to_do, part_info, params):
        context.unsubscribe_all()
        child = context.block_view(self.params.mri)
        exposure = params.generator.duration - self.readout_time.value
        child.put_attribute_values(dict(
            exposure=exposure,
            imageMode="Multiple",
            numImages=steps_to_do,
            arrayCounter=completed_steps,
            arrayCallbacks=True))
        self.post_configure(child, params)

    def post_configure(self, child, params):
        if self.trigger_mode.value == "Hardware":
            # Start now
            self.start_future = child.start_async()

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, context, update_completed_steps):
        child = context.block_view(self.params.mri)
        child.arrayCounter.subscribe_value(update_completed_steps, self)
        if self.trigger_mode.value != "Hardware":
            # Start now
            self.start_future = child.start_async()
        context.wait_all_futures(self.start_future)

    @RunnableController.Abort
    @RunnableController.Pause
    def abort(self, context):
        child = context.block_view(self.params.mri)
        child.stop()

