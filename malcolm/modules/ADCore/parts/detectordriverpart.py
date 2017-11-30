from malcolm.core import method_takes, TimeoutError, REQUIRED
from malcolm.modules.ADCore.infos import UniqueIdInfo
from malcolm.modules.builtin.parts import StatefulChildPart
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanpointgenerator.vmetas import PointGeneratorMeta


# Args for configure()
configure_args = (
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED
)


class DetectorDriverPart(StatefulChildPart):
    # Attributes
    trigger_mode = None

    # Stored futures
    start_future = None

    # How many we are waiting for
    done_when_reaches = None

    # The offset we should apply to the arrayCounter to give us completedSteps
    completed_offset = None

    @RunnableController.Reset
    def reset(self, context):
        super(DetectorDriverPart, self).reset(context)
        self.abort(context)

    @RunnableController.ReportStatus
    def report_configuration(self, context):
        child = context.block_view(self.params.mri)
        infos = [UniqueIdInfo(child.arrayCounterReadback.value)]
        return infos

    @RunnableController.Configure
    @RunnableController.PostRunArmed
    @RunnableController.Seek
    @method_takes(*configure_args)
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params):
        context.unsubscribe_all()
        child = context.block_view(self.params.mri)
        fs = self.setup_detector(child, completed_steps, steps_to_do, params)
        context.wait_all_futures(fs)
        self.done_when_reaches = child.arrayCounterReadback.value + steps_to_do
        self.completed_offset = completed_steps - child.arrayCounterReadback.value
        if self.is_hardware_triggered(child):
            # Start now if we are hardware triggered
            self.start_future = child.start_async()

    def is_hardware_triggered(self, child):
        return True

    def setup_detector(self, child, completed_steps, steps_to_do, params=None):
        if completed_steps == 0:
            # This is an initial configure, so reset arrayCounter to 0
            values = dict(arrayCounter=0)
        else:
            # Leave the arrayCounter where it is, just start from here
            values = {}

        # Not all areaDetector drivers support the imageMode of Multiple
        if "Multiple" in child.imageMode.meta.choices:
            values.update(dict(imageMode="Multiple"))

        values.update(dict(
            numImages=steps_to_do,
            arrayCallbacks=True))
        fs = child.put_attribute_values_async(values)
        return fs

    def update_completed_steps(self, value, update_completed_steps):
        completed_steps = value + self.completed_offset
        update_completed_steps(completed_steps, self)

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, context, update_completed_steps):
        child = context.block_view(self.params.mri)
        child.arrayCounterReadback.subscribe_value(
            self.update_completed_steps, update_completed_steps)
        if not self.is_hardware_triggered(child):
            # Start now
            self.start_future = child.start_async()
        context.wait_all_futures(self.start_future)
        # Now wait for up to 2*minDelta time to make sure any
        # update_completed_steps come in
        try:
            child.when_value_matches(
                "arrayCounterReadback", self.done_when_reaches, timeout=5.0)
        except TimeoutError:
            raise ValueError("Detector %r didn't produce %s frames in time" % (
                self.params.mri, self.done_when_reaches))

    @RunnableController.Abort
    @RunnableController.Pause
    def abort(self, context):
        child = context.block_view(self.params.mri)
        child.stop()
