from malcolm.core import Controller, DefaultStateMachine, Hook, \
    method_writeable_in, method_takes


sm = DefaultStateMachine


@method_takes()
class DefaultController(Controller):
    # The stateMachine that this controller implements
    stateMachine = sm()

    Reset = Hook()
    """Called at reset() to reset all parts to a known good state

    Args:
        task (Task): The task used to perform operations on child blocks
    """

    Disable = Hook()
    """Called at disable() to stop all parts updating their attributes

    Args:
        task (Task): The task used to perform operations on child blocks
    """

    @method_takes()
    def disable(self):
        self.try_stateful_function(sm.DISABLING, sm.DISABLED, self.do_disable)

    def do_disable(self):
        self.run_hook(self.Disable, self.create_part_tasks())

    @method_writeable_in(sm.DISABLED, sm.FAULT)
    def reset(self):
        self.try_stateful_function(
            sm.RESETTING, self.stateMachine.AFTER_RESETTING, self.do_reset)

    def do_reset(self):
        self.run_hook(self.Reset, self.create_part_tasks())

    def go_to_error_state(self, exception):
        self.log_exception("Fault occurred while running stateful function")
        self.transition(sm.FAULT, str(exception))

    def try_stateful_function(self, start_state, end_state, func, *args,
                              **kwargs):
        try:
            self.transition(start_state, start_state)
            func(*args, **kwargs)
            self.transition(end_state, end_state)
        except Exception as e:  # pylint:disable=broad-except
            self.go_to_error_state(e)
            raise
