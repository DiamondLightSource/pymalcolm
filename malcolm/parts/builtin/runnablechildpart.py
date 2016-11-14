from malcolm.core import method_takes, Task
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController


sm = RunnableController.stateMachine


class RunnableChildPart(ChildPart):
    # stored between runs
    run_future = None

    def update_configure_validate_args(self):
        # Decorate validate and configure with the sum of its parts
        method_metas = [self.child["configure"]]
        self.method_metas["validate"].recreate_from_others(method_metas)
        self.method_metas["configure"].recreate_from_others(method_metas)

    @RunnableController.Reset
    def reset(self, task):
        # Wait until we are Idle
        if self.child["abort"].writeable:
            task.post(self.child["abort"])
        try:
            task.post(self.child["reset"])
        except ValueError:
            # We get a "ValueError: child is not writeable" if we can't run
            # reset, probably because the child is already resetting,
            # so just wait for it to be idle
            task.when_matches(
                self.child["state"], sm.IDLE, bad_values=[sm.FAULT])
        self.update_configure_validate_args()

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
        task.subscribe(
            self.child["completedSteps"], update_completed_steps, self)
        self.run_future = task.post_async(self.child["run"])
        bad_states = [sm.DISABLING, sm.ABORTING, sm.FAULT]
        task.when_matches(self.child["state"], sm.POSTRUN, bad_states)

    @RunnableController.PostRunIdle
    @RunnableController.PostRunReady
    def post_run(self, task, completed_steps=None, steps_to_do=None,
                 part_info=None, params=None):
        task.wait_all(self.run_future)

    @RunnableController.Pause
    def pause(self, task):
        task.post(self.child["pause"])

    @RunnableController.Seek
    def seek(self, task, completed_steps, steps_to_do, part_info):
        params = self.child["seek"].prepare_input_map(
            completedSteps=completed_steps)
        task.post(self.child["seek"], params)

    @RunnableController.Resume
    def resume(self, task, update_completed_steps):
        task.post(self.child["resume"])

    @RunnableController.Abort
    def abort(self, task):
        task.post(self.child["abort"])
