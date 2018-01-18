from annotypes import TYPE_CHECKING

from malcolm.compat import OrderedDict
from malcolm.core import Alarm, MethodModel, AttributeModel, ProcessStartHook, \
    ProcessStopHook, ChoiceMeta, Hook, Widget, Context, Part, Request
from malcolm.modules.builtin.util import StatefulStates
from .basiccontroller import BasicController, AMri, ADescription, AUseCothread
from ..hooks import InitHook, ResetHook, DisableHook, HaltHook
from ..infos import HealthInfo, NotifyDispatchInfo

if TYPE_CHECKING:
    from typing import Union, Dict, Callable
    Field = Union[AttributeModel, MethodModel]
    ChildrenWriteable = Dict[str, Dict[Field, bool]]
    NotifyDispatchCallbacks = Dict[object, Callable[[Request], None]]


ss = StatefulStates


class StatefulController(BasicController):
    """A controller that implements `StatefulStates`"""
    # The stateSet that this controller implements
    state_set = ss()

    def __init__(self, mri, description="", use_cothread=True):
        # type: (AMri, ADescription, AUseCothread) -> None
        super(StatefulController, self).__init__(mri, description, use_cothread)
        self._children_writeable = {}  # type: ChildrenWriteable
        self._notify_dispatch_callbacks = {}  # type: NotifyDispatchCallbacks
        self.state = ChoiceMeta(
            "StateMachine State of Block", self.state_set.possible_states,
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model(ss.DISABLING)
        self.field_registry.add_attribute_model("state", self.state)
        self.field_registry.add_method_model(self.disable)
        self.set_writeable_in(self.field_registry.add_method_model(self.reset),
                              ss.DISABLED, ss.FAULT)
        self.info_registry.add_reportable(
            NotifyDispatchInfo, self.update_notify_dispatch)
        self.transition(ss.DISABLED)

    def set_writeable_in(self, field, *states):
        # Field has defined when it should be writeable, just check that
        # this is valid for this stateSet
        for state in states:
            assert state in self.state_set.possible_states, \
                "State %s is not one of the valid states %s" % \
                (state, self.state_set.possible_states)
        for state in self.state_set.possible_states:
            state_writeable = self._children_writeable.setdefault(state, {})
            state_writeable[field] = state in states

    def create_part_contexts(self):
        # type: () -> Dict[Part, Context]
        part_contexts = OrderedDict()
        for part in self.parts.values():
            context = Context(self.process)
            try:
                context.set_notify_dispatch_request(
                    self._notify_dispatch_callbacks[part])
            except KeyError:
                # The part doesn't want to be notified
                pass
            part_contexts[part] = context
        return part_contexts

    def update_notify_dispatch(self, reporter, info):
        # type: (object, NotifyDispatchInfo) -> None
        """The reporter wants to be notified by the context"""
        self._notify_dispatch_callbacks[reporter] = info.notify_dispatch

    def on_hook(self, hook):
        # type: (Hook) -> None
        if isinstance(hook, ProcessStartHook):
            hook.run(self.do_init)
        elif isinstance(hook, ProcessStopHook):
            hook.run(self.halt)

    def init(self):
        self.try_stateful_function(ss.RESETTING, ss.READY, self.do_init)

    def do_init(self):
        self.run_hooks(InitHook(part, context)
                       for part, context in self.create_part_contexts().items())

    def halt(self):
        self.run_hooks(HaltHook(part, context)
                       for part, context in self.create_part_contexts().items())
        self.disable()

    def disable(self):
        self.try_stateful_function(ss.DISABLING, ss.DISABLED, self.do_disable)

    def do_disable(self):
        self.run_hooks(DisableHook(part, context)
                       for part, context in self.create_part_contexts().items())

    def reset(self):
        self.try_stateful_function(ss.RESETTING, ss.READY, self.do_reset)

    def do_reset(self):
        self.run_hooks(ResetHook(part, context)
                       for part, context in self.create_part_contexts().items())

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
            if self.state_set.transition_allowed(
                    initial_state=initial_state, target_state=state):
                self.log.debug(
                    "Transitioning from %s to %s", initial_state, state)
                if state == ss.DISABLED:
                    alarm = Alarm.invalid("Disabled")
                elif state == ss.FAULT:
                    alarm = Alarm.major(message)
                else:
                    alarm = Alarm()
                self.update_health(self, HealthInfo(alarm))
                self.state.set_value(state)
                self.state.set_alarm(alarm)
                for child, writeable in self._children_writeable[state].items():
                    if isinstance(child, AttributeModel):
                        child.meta.set_writeable(writeable)
                    elif isinstance(child, MethodModel):
                        child.set_writeable(writeable)
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
            self.log.exception(
                "Exception running %s %s %s transitioning from %s to %s",
                func, args, kwargs, start_state, end_state)
            self.go_to_error_state(e)
            raise

    def add_block_field(self, name, child, writeable_func):
        super(StatefulController, self).add_block_field(
            name, child, writeable_func)
        # If we don't have a writeable func it can never be writeable
        if writeable_func is None:
            return
        # If we have already registered an explicit set then we are done
        for state in self.state_set.possible_states:
            state_writeable = self._children_writeable.get(state, {})
            if child in state_writeable:
                return
        # Field is writeable but has not defined when it should be
        # writeable, so calculate it from the possible states
        states = [
            state for state in self.state_set.possible_states
            if state not in (ss.DISABLING, ss.DISABLED)]
        for state in self.state_set.possible_states:
            state_writeable = self._children_writeable.setdefault(state, {})
            state_writeable[child] = state in states
