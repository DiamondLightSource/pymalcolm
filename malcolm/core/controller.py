import inspect

from malcolm.core.loggable import Loggable
from malcolm.core.attribute import Attribute
from malcolm.core.hook import Hook
from malcolm.core.method import takes, only_in, Method, get_method_decorated
from malcolm.vmetas import ChoiceMeta, StringMeta, BooleanMeta
from malcolm.statemachines import DefaultStateMachine


sm = DefaultStateMachine


@sm.insert
class Controller(Loggable):
    """Implement the logic that takes a Block through its statemachine"""

    Resetting = Hook()

    def __init__(self, process, block, block_name):
        """
        Args:
            process (Process): The process this should run under
            block (Block): Block instance to add Methods and Attributes to
        """
        process.add_block(block_name, block)
        self.set_logger_name("%s.controller" % block_name)

        # dictionary of dictionaries
        # {state (str): {Method: writeable (bool)}
        self.methods_writeable = {}
        self.process = process
        self.parts = []
        self.block = block
        self._set_block_children()

    def _set_block_children(self):
        # reconfigure block with new children
        children = []
        children += list(self._create_default_attributes())
        children += list(self.create_attributes())
        children += list(self.create_methods())
        for part in self.parts:
            children += list(part.create_attributes())
            children += list(part.create_methods())
        # set methods_writeable
        self.methods_writeable = {}
        for method in [c for n, c in children if isinstance(c, Method)]:
            # Set if the method is writeable
            if method.only_in is None:
                states = [state for state in self.stateMachine.possible_states
                          if state != sm.DISABLED]
            else:
                states = method.only_in
                for state in states:
                    assert state in self.stateMachine.possible_states, \
                        "State %s is not one of the valid states %s" % \
                        (state, self.stateMachine.possible_states)
            self.set_method_writeable_in(method, states)

    def create_methods(self):
        """Abstract method that should provide Method instances for Block

        Yields:
            Method: Each one will be attached to the Block by calling
            block.add_method(method)
        """

        for name, member in inspect.getmembers(self, inspect.ismethod):
            if hasattr(member, "Method"):
                member.Method.set_function(member)
                yield (name, member.Method)

    def create_attributes(self):
        """Abstract method that should provide Attribute instances for Block

        Yields:
            Attribute: Each one will be attached to the Block by calling
            block.add_attribute(attribute)
        """
        return iter(())

    def _create_default_attributes(self):
        # Add the state, status and busy attributes
        self.state = Attribute(
            "state", ChoiceMeta(
                "State of Block", self.stateMachine.possible_states))
        self.state.set_value(self.stateMachine.DISABLED)
        yield (self.state, None)
        self.status = Attribute(
            "status", StringMeta("Status of Block"))
        self.status.set_value("Disabled")
        yield (self.status, None)
        self.busy = Attribute(
            "busy", BooleanMeta("Whether Block busy or not"))
        self.busy.set_value(False)
        yield (self.busy, None)
        self.block.set_children(children)

    def create_attributes(self):
        """Abstract method that should provide Attribute instances for Block

        Yields:
            tuple: (attribute Attribute, callable put_function). Each attribute
            will be attached to the Block by calling
            block.add_child(attribute, put_function)
        """
        return iter(())

    def create_methods(self):
        """Abstract method that should provide Method instances for Block

        Yields:
            Method: Each one will be attached to the Block by calling
            block.add_method(method)
        """
        for func in get_method_decorated(self):
            yield (func.Method, func)

    def set_parts(self, parts):
        """Set the parts that contribute Attributes and Methods to the block

        Args:
            parts (list): List of Part instances
        """
        self.parts = parts
        self._set_block_children()

    def transition(self, state, message):
        """
        Change to a new state if the transition is allowed

        Args:
            state(str): State to transition to
            message(str): Status message
        """

        if self.stateMachine.is_allowed(
                initial_state=self.state.value, target_state=state):

            # transition is allowed, so set attributes
            self.state.set_value(state, notify=False)
            self.status.set_value(message, notify=False)
            is_busy = state in self.stateMachine.busy_states
            self.busy.set_value(is_busy, notify=False)

            # say which methods can now be called
            for method in self.block.methods.values():
                writeable = self.methods_writeable[state][method.name]
                method.set_writeable(writeable, notify=False)

            self.block.notify_subscribers()
        else:
            raise TypeError("Cannot transition from %s to %s" %
                            (self.state.value, state))

    def set_method_writeable_in(self, method, states):
        """
        Set the states that the given method can be called in

        Args:
            method(Method): Method that will be set writeable or not
            states(list[str]): List of states where method is writeable
        """
        for state in self.stateMachine.possible_states:
            writeable_dict = self.methods_writeable.setdefault(state, {})
            is_writeable = state in states
            writeable_dict[method.name] = is_writeable

    @takes()
    @only_in(sm.DISABLED, sm.FAULT)
    def reset(self):
        try:
            self.transition(sm.RESETTING, "Resetting")
            self.Resetting.run(self)
            self.transition(sm.AFTER_RESETTING, "Done resetting")
        except Exception as e:
            self.log_exception("Fault occurred while Resetting")
            self.transition(sm.FAULT, str(e))

    @takes()
    def disable(self):
        self.transition(sm.DISABLED, "Disabled")
