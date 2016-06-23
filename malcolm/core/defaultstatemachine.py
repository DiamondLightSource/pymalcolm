from malcolm.core.statemachine import StateMachine

class DefaultStateMachine(StateMachine):

    READY = "Ready"

    def create_states(self):
        self.set_allowed(self.RESETTING, self.READY)
