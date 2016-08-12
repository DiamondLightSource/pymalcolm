from collections import OrderedDict

from malcolm.core.loggable import Loggable


class StateMachine(Loggable):

    RESETTING = "Resetting"
    DISABLED = "Disabled"
    DISABLING = "Disabling"
    FAULT = "Fault"

    # Subclasses must override this
    AFTER_RESETTING = None

    def __init__(self, name):
        self.set_logger_name(name)
        self.name = name
        self.allowed_transitions = OrderedDict()
        self.busy_states = []
        assert self.AFTER_RESETTING is not None, \
            "No AFTER_RESETTING state given"
        self.set_allowed(self.RESETTING, self.AFTER_RESETTING)
        self.set_busy(self.RESETTING)
        self.create_states()
        custom_states = list(self.allowed_transitions) + [self.AFTER_RESETTING]

        # Set transitions for standard states
        for state in custom_states:
            self.set_allowed(state, self.FAULT)
            self.set_allowed(state, self.DISABLING)
        self.set_allowed(self.FAULT, [self.RESETTING, self.DISABLING])
        self.set_allowed(self.DISABLING, [self.FAULT, self.DISABLED])
        self.set_allowed(self.DISABLED, self.RESETTING)

        # These are all the states we can possibly be in
        self.possible_states = list(self.allowed_transitions)

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
        assert initial_state in self.allowed_transitions, \
            "%s is not in %s" % (initial_state, list(self.allowed_transitions))
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


class DefaultStateMachine(StateMachine):

    READY = "Ready"

    AFTER_RESETTING = READY

    def create_states(self):
        pass


class RunnableDeviceStateMachine(StateMachine):

    READY = "Ready"
    IDLE = "Idle"
    CONFIGURING = "Configuring"
    PRERUN = "PreRun"
    RUNNING = "Running"
    POSTRUN = "PostRun"
    PAUSED = "Paused"
    REWINDING = "Rewinding"
    ABORTING = "Aborting"
    ABORTED = "Aborted"

    AFTER_RESETTING = IDLE

    def create_states(self):
        # Set transitions for normal states
        self.set_allowed(self.IDLE, self.CONFIGURING)
        self.set_allowed(
            self.READY, [self.PRERUN, self.REWINDING, self.RESETTING])
        self.set_allowed(self.CONFIGURING, self.READY)
        self.set_allowed(self.PRERUN, [self.RUNNING, self.REWINDING])
        self.set_allowed(self.RUNNING, [self.POSTRUN, self.REWINDING])
        self.set_allowed(self.POSTRUN, [self.IDLE, self.READY])
        self.set_allowed(self.PAUSED, [self.REWINDING, self.PRERUN])
        self.set_allowed(self.REWINDING, self.PAUSED)

        # Add Aborting to all normal states
        normal_states = [self.IDLE, self.READY, self.CONFIGURING, self.PRERUN,
                         self.RUNNING, self.POSTRUN, self.PAUSED,
                         self.RESETTING, self.REWINDING]
        for state in normal_states:
            self.set_allowed(state, self.ABORTING)

        # Set transitions for other states
        self.set_allowed(self.ABORTING, self.ABORTED)
        self.set_allowed(self.ABORTED, self.RESETTING)