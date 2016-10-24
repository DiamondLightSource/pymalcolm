from collections import OrderedDict

from malcolm.core import method_takes, Task, ElementMap
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController


sm = RunnableController.stateMachine


class RunnableChildPart(ChildPart):
    # stored between runs
    run_future = None

    @RunnableController.Reset
    def reset(self, task):
        # Wait until we are Idle
        if self.child.state == sm.RESETTING:
            task.when_matches(self.child["state"], sm.IDLE)
        else:
            if self.child["abort"].writeable:
                task.post(self.child["abort"])
            task.post(self.child["reset"])

        # Update our configure from our child
        takes_elements = OrderedDict()
        takes_elements.update(self.child["configure"].takes.elements.to_dict())
        takes = ElementMap(takes_elements)
        defaults = OrderedDict()
        defaults.update(self.child["configure"].defaults)

        # Decorate validate and configure with the sum of its parts
        self.method_metas["configure"].takes.set_elements(takes)
        self.method_metas["configure"].set_defaults(defaults)

    @RunnableController.Validate
    def validate(self, task, params, returns):
        returns.update(task.post(self.child["validate"], params))
        return returns

    # MethodMeta will be filled in by _update_configure_args
    @RunnableController.Configure
    @method_takes()
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        task.post(self.child["configure"], params)

    @RunnableController.Run
    def run(self, task, update_completed_steps):
        """Wait for run to finish
        Args:
            task (Task): The task helper
            update_completed_steps (func): The function we should call when
                completedSteps should be updated
        """
        self.log_error("Starting run")
        task.subscribe(
            self.child["completedSteps"], update_completed_steps, self)
        self.run_future = task.post_async(self.child["run"])
        bad_states = [sm.DISABLING, sm.ABORTING, sm.FAULT]
        self.log_error("Waiting for state")
        task.when_matches(self.child["state"], sm.POSTRUN, bad_states)
        self.log_error("Now in postrun state")

    @RunnableController.PostRunIdle
    @RunnableController.PostRunReady
    def post_run(self, task, completed_steps=None, steps_to_do=None,
                 part_info=None, params=None):
        self.log_error("Waiting for run to complete")
        task.wait_all(self.run_future)
        self.log_error("done waiting")

    @RunnableController.Pause
    def pause(self, task):
        task.post(self.child["pause"])

    @RunnableController.Seek
    def seek(self, task, completed_steps, steps_to_do, part_info, params):
        task.post(self.child["seek"])

    @RunnableController.Resume
    def resume(self, task, update_completed_steps):
        task.post(self.child["resume"])

    @RunnableController.Abort
    def abort(self, task):
        task.post(self.child["abort"])
