from malcolm.core import Controller, DefaultStateMachine, Hook, \
    method_only_in, method_takes


sm = DefaultStateMachine


@sm.insert
@method_takes()
class DefaultController(Controller):

    Resetting = Hook()
    Disabling = Hook()

    @method_takes()
    def disable(self):
        try:
            self.transition(sm.DISABLING, "Disabling")
            self.do_disable()
            self.transition(sm.DISABLED, "Done Disabling")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Disabling")
            self.transition(sm.FAULT, str(e))
            raise

    def do_disable(self):
        self.run_hook(self.Disabling, self.create_part_tasks())

    @method_only_in(sm.DISABLED, sm.FAULT)
    def reset(self):
        try:
            self.transition(sm.RESETTING, "Resetting")
            self.do_reset()
            self.transition(self.stateMachine.AFTER_RESETTING, "Done Resetting")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Resetting")
            self.transition(sm.FAULT, str(e))
            raise

    def do_reset(self):
        self.run_hook(self.Resetting, self.create_part_tasks())
