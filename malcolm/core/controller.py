import inspect

from malcolm.core.loggable import Loggable


class Controller(Loggable):
    """Implement the logic that takes a Block through its statemachine"""

    def __init__(self, block):
        """
        Args:
            block (Block): Block instance to add Methods and Attributes to
        """
        logger_name = "%s.controller" % block.name
        super(Controller, self).__init__(logger_name)
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
