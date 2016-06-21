import inspect
from collections import OrderedDict

from malcolm.core.loggable import Loggable
from malcolm.core.statemachine import StateMachine
from malcolm.core.attribute import Attribute
from malcolm.core.enummeta import EnumMeta
from malcolm.core.stringmeta import StringMeta
from malcolm.core.booleanmeta import BooleanMeta


@StateMachine.insert
class Controller(Loggable):
    """Implement the logic that takes a Block through its statemachine"""

    def __init__(self, block):
        """
        Args:
            block (Block): Block instance to add Methods and Attributes to
        """
        logger_name = "%s.controller" % block.name
        super(Controller, self).__init__(logger_name)

        enum_meta = EnumMeta("State", "State of Block", [])
        self.state = Attribute(enum_meta)
        string_meta = StringMeta("Status", "Status of Block")
        self.status = Attribute(string_meta)
        boolean_meta = BooleanMeta("Busy", "Whether Block busy or not")
        self.busy = Attribute(boolean_meta)

        self.writeable_methods = OrderedDict()

        self.block = block
        for attribute in self.create_attributes():
            block.add_attribute(attribute)
        for method in self.create_methods():
            block.add_method(method)

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
        return iter(())

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

            for method in self.block._methods.values():
                if method in self.writeable_methods[state]:
                    self.block._methods[method].set_writeable(True)
                else:
                    self.block._methods[method].set_writeable(False)

            self.block.notify_subscribers()

        else:
            raise TypeError("Cannot transition from %s to %s" %
                            (self.state.value, state))

    def set_writeable_methods(self, state, methods):
        """
        Set the methods that can be changed in the given state

        Args:
            state(list(str)): States to set writeable
            methods(Method): Method to set states for
        """

        self.writeable_methods[state] = [method.name for method in methods]
