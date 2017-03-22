from malcolm.controllers.scanpointgenerator.runnablecontroller import RunnableController
from malcolm.core import method_takes
from malcolm.parts.pandabox.pandaboxchildpart import PandABoxChildPart


class PandABoxDriverPart(PandABoxChildPart):
    # Stored futures
    start_future = None

    @RunnableController.Reset
    def reset(self, task):
        super(PandABoxDriverPart, self).reset(task)
        self.abort(task)

    @RunnableController.Configure
    @RunnableController.PostRunReady
    @RunnableController.Seek
    @method_takes()
    def configure(self, task, completed_steps, steps_to_do, part_info):
        task.unsubscribe_all()
        task.put_many(self.child, dict(
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

