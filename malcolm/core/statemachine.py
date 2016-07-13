from collections import OrderedDict

from malcolm.core.loggable import Loggable


class StateMachine(Loggable):

    RESETTING = "Resetting"
    DISABLED = "Disabled"
    FAULT = "Fault"

    def __init__(self, name):
        self.set_logger_name(name)
        self.name = name
        self.allowed_transitions = OrderedDict()
        self.busy_states = []
        self.create_states()
        self.possible_states = list(self.allowed_transitions)
        assert self.RESETTING in self.possible_states, \
            "A transition from RESETTING must be provided"

        # Set transitions for standard states
        self.set_allowed(self.FAULT, [self.RESETTING, self.DISABLED])
        self.set_allowed(self.DISABLED, self.RESETTING)
        for state in self.possible_states:
            self.set_allowed(state, self.FAULT)
            self.set_allowed(state, self.DISABLED)
        self.possible_states.append(self.FAULT)
        self.possible_states.append(self.DISABLED)

    def create_states(self):
        raise NotImplementedError()

    def is_allowed(self, initial_state, target_state):
        """
        Check if a transition between two states is allowed

        Args:
            initial_state(str): Initial state
            target_state(str): Target state

        Returns:
            bool: True if allowed, False if not
        """

        return target_state in self.allowed_transitions[initial_state]

    def set_allowed(self, initial_state, allowed_states):
        """
        Add an allowed transition state

        Args:
            initial_state(str): Initial state
            allowed_states(list(str) / str): States that initial_state can
            transition to
        """

        if not isinstance(allowed_states, list):
            allowed_states = [allowed_states]

        self.allowed_transitions.setdefault(initial_state, set()).update(
            allowed_states)

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
