from malcolm.core import method_takes, Task, serialize_object
from malcolm.core import ResponseError, BadValueError
from malcolm.parts.builtin.childpart import ChildPart
from malcolm.controllers.runnablecontroller import RunnableController, \
    ParameterTweakInfo


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
        except ResponseError:
            # We get a "ResponseError: child is not writeable" if we can't run
            # reset, probably because the child is already resetting,
            # so just wait for it to be idle
            task.when_matches(
                self.child["state"], sm.IDLE, bad_values=[sm.FAULT])
        self.update_configure_validate_args()

    # MethodMeta will be filled in by _update_configure_args
    @RunnableController.Validate
    @method_takes()
    def validate(self, task, part_info, params):
        returns = task.post(self.child["validate"], params)
        ret = []
        for k, v in returns.items():
            if serialize_object(params[k]) != serialize_object(v):
                ret.append(ParameterTweakInfo(k, v))
        return ret

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
        task.unsubscribe_all()
        task.subscribe(
            self.child["completedSteps"], update_completed_steps, self)
        match_future = self._wait_for_postrun(task)
        self.run_future = task.post_async(self.child["run"])
        try:
            task.wait_all(match_future)
        except BadValueError:
            # If child went into Fault state, raise the friendlier run_future
            # exception
            if self.child.state == sm.FAULT:
                raise self.run_future[0].exception()
            raise

    @RunnableController.PostRunIdle
    @RunnableController.PostRunReady
    def post_run(self, task, completed_steps=None, steps_to_do=None,
                 part_info=None, params=None):
        task.wait_all(self.run_future)

    @RunnableController.Seek
    def seek(self, task, completed_steps, steps_to_do, part_info):
        # Clear out the update_completed_steps and match_future subscriptions
        task.unsubscribe_all()
        params = self.child["pause"].prepare_input_map(
            completedSteps=completed_steps)
        task.post(self.child["pause"], params)

    @RunnableController.Resume
    def resume(self, task, update_completed_steps):
        task.subscribe(
            self.child["completedSteps"], update_completed_steps, self)
        match_future = self._wait_for_postrun(task)
        task.post(self.child["resume"])
        task.wait_all(match_future)

    def _wait_for_postrun(self, task):
        bad_states = [sm.DISABLING, sm.ABORTING, sm.FAULT]
        match_future = task.when_matches_async(
            self.child["state"], sm.POSTRUN, bad_states)
        return match_future

    @RunnableController.Abort
    def abort(self, task):
        task.post(self.child["abort"])
