import inspect
from collections import OrderedDict

from malcolm.core.loggable import Loggable
from malcolm.core.attribute import Attribute
from malcolm.core.hook import Hook
from malcolm.core.method import takes, only_in
from malcolm.metas import ChoiceMeta, StringMeta, BooleanMeta
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
        for name, attribute in self._create_default_attributes():
            block.add_attribute(name, attribute)
        for name, attribute in self.create_attributes():
            block.add_attribute(name, attribute)
        for name, method in self.create_methods():
            block.add_method(name, method)
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
        self.state = Attribute(ChoiceMeta(description="State of Block",
                            choices=self.stateMachine.possible_states))
        self.state.set_parent(self.block,'state')
        self.state.set_value(self.stateMachine.DISABLED)
        yield ('state', self.state)
        self.status = Attribute(StringMeta(description="Status of Block"))
        self.status.set_value("Disabled")
        yield ('status', self.status)
        self.busy = Attribute(BooleanMeta(
            description="Whether Block busy or not"))
        self.busy.set_value(False)
        yield ('busy', self.busy)

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

    def add_parts(self, parts):
        self.parts.extend(parts)

    def transition(self, state, message):
        """
        Change to a new state if the transition is allowed

        Args:
            state(str): State to transition to
            message(str): Status message
        """

        if self.stateMachine.is_allowed(initial_state=self.state.value,
                                        target_state=state):

            self.state.set_value(state)

            if state in self.stateMachine.busy_states:
                self.busy.set_value(True)
            else:
                self.busy.set_value(False)

            self.status.set_value(message)

            for method in self.block.methods.values():
                writeable = self.methods_writeable[state][method.name]
                method.set_writeable(writeable)

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
