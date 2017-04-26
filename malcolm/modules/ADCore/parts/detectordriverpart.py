from malcolm.core import method_takes, TimeoutError
from malcolm.modules.builtin.parts import StatefulChildPart
from malcolm.modules.builtin.vmetas import ChoiceMeta
from malcolm.modules.scanning.controllers import RunnableController


class DetectorDriverPart(StatefulChildPart):
    # Attributes
    trigger_mode = None

    # Stored futures
    start_future = None

    # How many we are waiting for
    done_when_reaches = None

    def create_attributes(self):
        for data in super(DetectorDriverPart, self).create_attributes():
            yield data
        meta = ChoiceMeta("Whether detector is software or hardware triggered",
                          ["Software", "Hardware"])
        self.trigger_mode = meta.create_attribute("Hardware")
        yield "triggerMode", self.trigger_mode, None

    @RunnableController.Reset
    def reset(self, context):
        super(DetectorDriverPart, self).reset(context)
        self.abort(context)

    @RunnableController.Configure
    @RunnableController.PostRunReady
    @RunnableController.Seek
    @method_takes()
    def configure(self, context, completed_steps, steps_to_do, part_info,
                  params=None):
        context.unsubscribe_all()
        child = context.block_view(self.params.mri)
        self.done_when_reaches = completed_steps + steps_to_do
        fs = self.setup_detector(child, completed_steps, steps_to_do, params)
        context.wait_all_futures(fs)
        if self.trigger_mode.value == "Hardware":
            # Start now if we are hardware triggered
            self.start_future = child.start_async()

    def setup_detector(self, child, completed_steps, steps_to_do, params=None):
        fs = child.put_attribute_values_async(dict(
            imageMode="Multiple",
            numImages=steps_to_do,
            arrayCounter=completed_steps,
            arrayCallbacks=True))
        return fs

    @RunnableController.Run
    @RunnableController.Resume
    def run(self, context, update_completed_steps):
        child = context.block_view(self.params.mri)
        child.arrayCounter.subscribe_value(update_completed_steps, self)
        if self.trigger_mode.value != "Hardware":
            # Start now
            self.start_future = child.start_async()
        context.wait_all_futures(self.start_future)
        # Now wait for up to minDelta time to make sure any
        # update_completed_steps come in
        try:
            child.when_value_matches(
                "arrayCounter", self.done_when_reaches, timeout=0.1)
        except TimeoutError:
            raise ValueError("Detector %r didn't produce %s frames in time" % (
                self.params.mri, self.done_when_reaches))

    @RunnableController.Abort
    @RunnableController.Pause
    def abort(self, context):
        child = context.block_view(self.params.mri)
        child.stop()
