from collections import OrderedDict

from malcolm.core.loggable import Loggable


class StateMachine(Loggable):

    READY = "Ready"
    RESETTING = "Resetting"
    DISABLED = "Disabled"
    FAULT = "Fault"

    def __init__(self, name):
        super(StateMachine, self).__init__(logger_name=name)

        self.name = name
        self.allowed_transitions = OrderedDict()
        self.busy_states = []

    def is_allowed(self, state_1, state_2):
        """
        Check if a transition between two states is allowed

        Args:
            state_1(str): Initial state
            state_2(str): Target state

        Returns:
            bool: True if allowed, False if not
        """

        return state_2 in self.allowed_transitions[state_1]

    def set_allowed(self, state_1, state_2):
        """
        Add an allowed transition state

        Args:
            state_1(str): Initial state
            state_2(str): Target state
        """

        if state_1 in list(self.allowed_transitions.keys()):
            self.allowed_transitions[state_1].append(state_2)
        else:
            self.allowed_transitions[state_1] = [state_2]

    def set_busy(self, state, busy=True):
        """
        Set the busy-ness of a state; i.e. whether the block is considered
        to be busy in a certain state

        Args:
            state(str): State to update
            busy(bool): True or False for whether state is a busy state
        """

        if not busy and state in self.busy_states:
            self.busy_states.remove(state)

        elif busy and state not in self.busy_states:
            self.busy_states.append(state)

    def is_busy(self, state):
        """
        Check if a state is a busy state

        Args:
            state(str): State to check busy-ness for

        Returns:
            bool: True if state is a busy state, False if not
        """
        return state in self.busy_states

    @classmethod
    def insert(cls, controller):
        """
        Add a stateMachine to a Controller, overriding any current
        current StateMachine

        Args:
            controller(Controller): Controller to add stateMachine to

        Returns:
            Controller: Controller with stateMachine
        """

        controller.stateMachine = cls(cls.__name__)

        return controller
