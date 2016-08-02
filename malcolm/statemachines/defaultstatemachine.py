from malcolm.core import StateMachine


class DefaultStateMachine(StateMachine):

    READY = "Ready"

    AFTER_RESETTING = READY

    def create_states(self):
        pass
