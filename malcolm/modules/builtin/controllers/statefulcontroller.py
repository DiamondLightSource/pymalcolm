from malcolm.compat import OrderedDict
from malcolm.core import Hook, method_writeable_in, method_takes, Alarm, \
    MethodModel, AttributeModel, Process
from malcolm.modules.builtin.vmetas import ChoiceMeta
from .basiccontroller import BasicController


class StatefulStates(object):
    """The most basic Malcolm state machine"""

    RESETTING = "Resetting"
    DISABLED = "Disabled"
    DISABLING = "Disabling"
    FAULT = "Fault"
    READY = "Ready"

    def __init__(self):
        self._allowed = OrderedDict()
        # These are all the states we can possibly be in
        self.possible_states = []
        self.create_block_transitions()
        self.create_error_disable_transitions()

    def create_block_transitions(self):
        self.set_allowed(self.RESETTING, self.READY)

    def create_error_disable_transitions(self):
        block_states = self.possible_states[:]

        # Set transitions for standard states
        for state in block_states:
            self.set_allowed(state, self.FAULT)
            self.set_allowed(state, self.DISABLING)
        self.set_allowed(self.FAULT, [self.RESETTING, self.DISABLING])
        self.set_allowed(self.DISABLING, [self.FAULT, self.DISABLED])
        self.set_allowed(self.DISABLED, self.RESETTING)

    def transition_allowed(self, initial_state, target_state):
        """
        Check if a transition between two states is allowed

        Args:
            initial_state(str): Initial state
            target_state(str): Target state

        Returns:
            bool: True if allowed, False if not
        """
        assert initial_state in self._allowed, \
            "%s is not in %s" % (initial_state, list(self._allowed))
        return target_state in self._allowed[initial_state]

    def set_allowed(self, initial_state, allowed_states):
        """Add an allowed transition state

        Args:
            initial_state (str): Initial state
            allowed_states (str or list): state or list of states that
                initial_state can transition to
        """
        if not isinstance(allowed_states, list):
            allowed_states = [allowed_states]

        self._allowed.setdefault(initial_state, set()).update(allowed_states)
        for state in allowed_states + [initial_state]:
            if state not in self.possible_states:
                self.possible_states.append(state)


ss = StatefulStates


class StatefulController(BasicController):
    """A controller that implements `StatefulStates`"""
    # The stateSet that this controller implements
    stateSet = ss()
    # {state (str): {Meta/MethodMeta/Attribute: writeable (bool)}
    _children_writeable = None
    # Attributes
    state = None

    Init = Hook()
    """Called when this controller is told to start by the process

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
    """

    Halt = Hook()
    """Called when this controller is told to halt

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
    """

    Reset = Hook()
    """Called at reset() to reset all parts to a known good state

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
    """

    Disable = Hook()
    """Called at disable() to stop all parts updating their attributes

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
    """

    def __init__(self, process, parts, params):
        self._children_writeable = {}
        super(StatefulController, self).__init__(process, parts, params)
        self.transition(ss.DISABLED)

    def create_attribute_models(self):
        """MethodModel that should provide Attribute instances for Block

        Yields:
            tuple: (string name, Attribute, callable put_function).
        """
        for y in super(StatefulController, self).create_attribute_models():
            yield y
        # Create read-only attribute for current state string
        meta = ChoiceMeta(
            "State of Block", self.stateSet.possible_states, label="State")
        self.state = meta.create_attribute_model(ss.DISABLING)
        yield "state", self.state, None

    @Process.Init
    def init(self):
        self.try_stateful_function(ss.RESETTING, ss.READY, self.do_init)

    def do_init(self):
        self.run_hook(self.Init, self.create_part_contexts())

    @Process.Halt
    def halt(self):
        self.run_hook(self.Halt, self.create_part_contexts())
        self.disable()

    @method_takes()
    def disable(self):
        self.try_stateful_function(ss.DISABLING, ss.DISABLED, self.do_disable)

    def do_disable(self):
        self.run_hook(self.Disable, self.create_part_contexts())

    @method_writeable_in(ss.DISABLED, ss.FAULT)
    def reset(self):
        self.try_stateful_function(ss.RESETTING, ss.READY, self.do_reset)

    def do_reset(self):
        self.run_hook(self.Reset, self.create_part_contexts())

    def go_to_error_state(self, exception):
        if self.state.value != ss.FAULT:
            self.transition(ss.FAULT, str(exception))

    def transition(self, state, message=""):
        """Change to a new state if the transition is allowed

        Args:
            state (str): State to transition to
            message (str): Message if the transition is to a fault state
        """
        with self.changes_squashed:
            initial_state = self.state.value
            if self.stateSet.transition_allowed(
                    initial_state=initial_state, target_state=state):
                self.log.debug(
                    "Transitioning from %s to %s", initial_state, state)
                if state == ss.DISABLED:
                    alarm = Alarm.invalid("Disabled")
                elif state == ss.FAULT:
                    alarm = Alarm.major(message)
                else:
                    alarm = Alarm()
                self.update_health(self, alarm)
                self.state.set_value(state)
                self.state.set_alarm(alarm)
                for child, writeable in self._children_writeable[state].items():
                    if isinstance(child, AttributeModel):
                        child.meta.set_writeable(writeable)
                    elif isinstance(child, MethodModel):
                        child.set_writeable(writeable)
                        for element in child.takes.elements.values():
                            element.set_writeable(writeable)
            else:
                raise TypeError("Cannot transition from %s to %s" %
                                (initial_state, state))

    def try_stateful_function(self, start_state, end_state, func, *args,
                              **kwargs):
        try:
            self.transition(start_state)
            func(*args, **kwargs)
            self.transition(end_state)
        except Exception as e:  # pylint:disable=broad-except
            self.go_to_error_state(e)
            raise

    def add_block_field(self, name, child, writeable_func):
        super(StatefulController, self).add_block_field(
            name, child, writeable_func)
        # Set children_writeable dict
        if isinstance(child, AttributeModel):
            states = child.meta.writeable_in
        else:
            states = child.writeable_in
        if states:
            # Field has defined when it should be writeable, just check that
            # this is valid for this stateSet
            for state in states:
                assert state in self.stateSet.possible_states, \
                    "State %s is not one of the valid states %s" % \
                    (state, self.stateSet.possible_states)
        elif writeable_func is not None:
            # Field is writeable but has not defined when it should be
            # writeable, so calculate it from the possible states
            states = [
                state for state in self.stateSet.possible_states
                if state not in (ss.DISABLING, ss.DISABLED)]
        else:
            # Field is never writeable, so will never need to change state
            return
        for state in self.stateSet.possible_states:
            state_writeable = self._children_writeable.setdefault(state, {})
            state_writeable[child] = state in states
