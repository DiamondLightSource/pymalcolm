import inspect
from collections import OrderedDict

from malcolm.core.loggable import Loggable
from malcolm.core.defaultstatemachine import DefaultStateMachine
from malcolm.core.attribute import Attribute
from malcolm.core.choicemeta import ChoiceMeta
from malcolm.core.stringmeta import StringMeta
from malcolm.core.booleanmeta import BooleanMeta
from malcolm.core.hook import Hook
from malcolm.core.method import takes


@DefaultStateMachine.insert
class Controller(Loggable):
    """Implement the logic that takes a Block through its statemachine"""

    Resetting = Hook()

    def __init__(self, process, block):
        """
        Args:
            process (Process): The process this should run under
            block (Block): Block instance to add Methods and Attributes to
        """
        self.set_logger_name("%s.controller" % block.name)

        self.writeable_methods = OrderedDict()
        self.process = process
        self.parts = []
        self.block = block
        for attribute in self.create_attributes():
            block.add_attribute(attribute)
        for method in self.create_methods():
            block.add_method(method)

        self.process.add_block(block)

    def create_methods(self):
        """Abstract method that should provide Method instances for Block

        Yields:
            Method: Each one will be attached to the Block by calling
            block.add_method(method)
        """

        members = [value[1] for value in
                   inspect.getmembers(self, predicate=inspect.ismethod)]

        for member in members:
            if hasattr(member, "Method"):
                member.Method.set_function(member)
                yield member.Method

    def create_attributes(self):
        """Abstract method that should provide Attribute instances for Block

        Yields:
            Attribute: Each one will be attached to the Block by calling
            block.add_attribute(attribute)
        """
        self.state = Attribute("State", ChoiceMeta(
            "meta", "State of Block",
            self.stateMachine.possible_states))
        yield self.state
        self.status = Attribute(
            "Status", StringMeta("meta", "Status of Block"))
        yield self.status
        self.busy = Attribute(
            "Busy", BooleanMeta("meta", "Whether Block busy or not"))
        yield self.busy

    @takes()
    def reset(self):
        sm = self.stateMachine
        try:
            self.transition(sm.RESETTING, "Resetting")
            self.Resetting.run()
            self.transition(sm.AFTER_RESETTING, "Done resetting")
        except Exception as e:
            self.log_exception("Fault occurred while Resetting")
            self.transition(sm.FAULT, str(e))

    @takes()
    def disable(self):
        self.transition(self.stateMachine.DISABLED, "Disabled")

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
                if method in self.writeable_methods[state]:
                    self.block.methods[method].set_writeable(True)
                else:
                    self.block.methods[method].set_writeable(False)

            self.block.notify_subscribers()

        else:
            raise TypeError("Cannot transition from %s to %s" %
                            (self.state.value, state))

    def set_writeable_methods(self, state, methods):
        """
        Set the methods that can be changed in the given state

        Args:
            state(str): State to set writeable methods in
            methods(list(Method)): Methods to set writeable
        """

        self.writeable_methods[state] = [method.name for method in methods]
