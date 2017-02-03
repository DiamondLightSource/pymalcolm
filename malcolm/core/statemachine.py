from malcolm.compat import OrderedDict
from malcolm.core.loggable import Loggable


class StateMachine(Loggable):

    RESETTING = "Resetting"
    DISABLED = "Disabled"
    DISABLING = "Disabling"
    FAULT = "Fault"

    # Subclasses must override this
    AFTER_RESETTING = None

    def __init__(self):
        self.set_logger_name(type(self).__name__)
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


class DefaultStateMachine(StateMachine):

    READY = "Ready"

    AFTER_RESETTING = READY

    def create_states(self):
        pass


class ManagerStateMachine(DefaultStateMachine):

    EDITABLE = "Editable"
    SAVING = "Saving"
    REVERTING = "Reverting"

    def create_states(self):
        super(ManagerStateMachine, self).create_states()
        self.set_allowed(self.AFTER_RESETTING, self.EDITABLE)
        self.set_allowed(self.EDITABLE, self.SAVING)
        self.set_allowed(self.EDITABLE, self.REVERTING)
        self.set_allowed(self.SAVING, self.AFTER_RESETTING)
        self.set_allowed(self.REVERTING, self.AFTER_RESETTING)


class RunnableStateMachine(ManagerStateMachine):

    IDLE = "Idle"
    CONFIGURING = "Configuring"
    READY = "Ready"
    RUNNING = "Running"
    POSTRUN = "PostRun"
    PAUSED = "Paused"
    SEEKING = "Seeking"
    ABORTING = "Aborting"
    ABORTED = "Aborted"

    AFTER_RESETTING = IDLE

    def create_states(self):
        super(RunnableStateMachine, self).create_states()
        # Set transitions for normal states
        self.set_allowed(self.IDLE, self.CONFIGURING)
        self.set_allowed(
            self.READY, [self.RUNNING, self.SEEKING, self.RESETTING])
        self.set_allowed(self.CONFIGURING, self.READY)
        self.set_allowed(self.RUNNING, [self.POSTRUN, self.SEEKING])
        self.set_allowed(self.POSTRUN, [self.IDLE, self.READY])
        self.set_allowed(self.PAUSED, [self.SEEKING, self.RUNNING])
        self.set_allowed(self.SEEKING, [self.READY, self.PAUSED])

        # Add Abort to all normal states
        normal_states = [
            self.IDLE, self.READY, self.CONFIGURING, self.RUNNING, self.POSTRUN,
            self.PAUSED, self.SEEKING]
        for state in normal_states:
            self.set_allowed(state, self.ABORTING)

        # Set transitions for other states
        self.set_allowed(self.ABORTING, self.ABORTED)
        self.set_allowed(self.ABORTED, self.RESETTING)
