import functools
from collections import OrderedDict

from malcolm.core.attribute import Attribute
from malcolm.core.block import Block
from malcolm.core.blockmeta import BlockMeta
from malcolm.core.hook import Hook
from malcolm.core.loggable import Loggable
from malcolm.core.methodmeta import method_takes, method_only_in, MethodMeta, \
    get_method_decorated
from malcolm.core.statemachine import DefaultStateMachine
from malcolm.core.vmetas import BooleanMeta, ChoiceMeta, StringMeta
from malcolm.core.request import Post


sm = DefaultStateMachine


@sm.insert
@method_takes()
class Controller(Loggable):
    """Implement the logic that takes a Block through its state machine"""

    # Attributes for all controllers
    state = None
    status = None
    busy = None
    # BlockMeta for descriptions
    meta = None

    def __init__(self, block_name, process, parts=None, params=None):
        """
        Args:
            process (Process): The process this should run under
        """
        controller_name = "%s(%s)" % (type(self).__name__, block_name)
        self.set_logger_name(controller_name)
        self.block = Block()
        self.log_debug("Creating block %r as %r" % (self.block, block_name))
        self.block_name = block_name
        self.params = params
        self.process = process
        self.lock = process.create_lock()
        # dictionary of dictionaries
        # {state (str): {MethodMeta: writeable (bool)}
        self.methods_writeable = {}
        if parts is None:
            parts = {}
        self.parts = parts
        for part_name, part in self.parts.items():
            part.set_logger_name("%s.%s" % (controller_name, part_name))

        self._set_block_children()
        self._do_transition(sm.DISABLED, "Disabled")
        self.block.set_parent(process, block_name)
        process.add_block(self.block)
        self.do_initial_reset()

    def do_initial_reset(self):
        request = Post(
            None, self.process.create_queue(), [self.block_name, "reset"])
        self.process.q.put(request)

    def add_change(self, changes, item, attr, value):
        path = item.path_relative_to(self.block) + [attr]
        changes.append([path, value])

    def _set_block_children(self):
        # reconfigure block with new children
        child_list = [self.create_meta()]
        child_list += list(self._create_default_attributes())
        child_list += list(self.create_attributes())
        child_list += list(self.create_methods())
        for part in self.parts.values():
            child_list += list(part.create_attributes())
            child_list += list(part.create_methods())

        self.methods_writeable = {}
        writeable_functions = {}
        children = OrderedDict()

        for name, child, writeable_func in child_list:
            if isinstance(child, MethodMeta):
                # Set if the method is writeable
                if child.only_in is None:
                    states = [
                        state for state in self.stateMachine.possible_states
                        if state not in (sm.DISABLING, sm.DISABLED)]
                else:
                    states = child.only_in
                    for state in states:
                        assert state in self.stateMachine.possible_states, \
                            "State %s is not one of the valid states %s" % \
                            (state, self.stateMachine.possible_states)
                # Make a copy otherwise all instances will own the same one
                child = MethodMeta.from_dict(child.to_dict())
                self.register_method_writeable(child, states)
            children[name] = child
            if writeable_func:
                writeable_functions[name] = functools.partial(
                    self.call_writeable_function, writeable_func)

        self.block.replace_endpoints(children)
        self.block.set_writeable_functions(writeable_functions)

    def call_writeable_function(self, function, child, *args):
        with self.lock:
            if not child.writeable:
                child.log_error("I'm not writeable")
                raise ValueError("Child %r is not writeable" % (child,))
        result = function(*args)
        return result

    def _create_default_attributes(self):
        # Add the state, status and busy attributes
        self.state = Attribute(
            ChoiceMeta("State of Block", self.stateMachine.possible_states))
        yield ("state", self.state, None)
        self.status = Attribute(StringMeta("Status of Block"))
        yield ("status", self.status, None)
        self.busy = Attribute(BooleanMeta("Whether Block busy or not"))
        yield ("busy", self.busy, None)

    def create_meta(self):
        self.meta = BlockMeta()
        return "meta", self.meta, None

    def create_attributes(self):
        """Method that should provide Attribute instances for Block

        Yields:
            tuple: (string name, Attribute, callable put_function).
        """
        return iter(())

    def create_methods(self):
        """Method that should provide MethodMeta instances for Block

        Yields:
            tuple: (string name, MethodMeta, callable post_function).
        """
        return get_method_decorated(self)

    def transition(self, state, message):
        """
        Change to a new state if the transition is allowed

        Args:
            state(str): State to transition to
            message(str): Status message
        """
        with self.lock:
            if self.stateMachine.is_allowed(
                    initial_state=self.state.value, target_state=state):
                self._do_transition(state, message)
            else:
                raise TypeError("Cannot transition from %s to %s" %
                                (self.state.value, state))

    def _do_transition(self, state, message):
        # transition is allowed, so set attributes
        changes = []
        self.add_change(changes, self.state, "value", state)
        self.add_change(changes, self.status, "value", message)
        self.add_change(changes, self.busy, "value",
                        state in self.stateMachine.busy_states)

        # say which methods can now be called
        for name in self.block:
            child = self.block[name]
            if isinstance(child, MethodMeta):
                method = child
                writeable = self.methods_writeable[state][method]
                self.log_debug("Setting %s %s to writeable %s", name, method, writeable)
                self.add_change(changes, method, "writeable", writeable)
                for ename in method.takes.elements:
                    meta = method.takes.elements[ename]
                    self.add_change(changes, meta, "writeable", writeable)

        self.block.apply_changes(*changes)

    def register_method_writeable(self, method, states):
        """
        Set the states that the given method can be called in

        Args:
            method(MethodMeta): Method that will be set writeable or not
            states(list[str]): List of states where method is writeable
        """
        for state in self.stateMachine.possible_states:
            writeable_dict = self.methods_writeable.setdefault(state, {})
            is_writeable = state in states
            writeable_dict[method] = is_writeable

