from malcolm.core import Controller, DefaultStateMachine, Hook, \
    method_only_in, method_takes


sm = DefaultStateMachine


@sm.insert
@method_takes()
class DefaultController(Controller):

    Resetting = Hook()

    @method_takes()
    def disable(self):
        self.transition(sm.DISABLED, "Disabled")

    @method_only_in(sm.DISABLED, sm.FAULT)
    def reset(self):
        try:
            self.transition(sm.RESETTING, "Resetting")
            self.Resetting.run(self)
            self.transition(sm.AFTER_RESETTING, "Done resetting")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Resetting")
            self.transition(sm.FAULT, str(e))
            raise