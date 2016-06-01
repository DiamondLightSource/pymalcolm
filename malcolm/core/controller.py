from loggable import Loggable


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
        for method in self.create_methods():
            block.add_method(method)

    def create_methods(self):
        """Abstract method that should provide Method instances for Block

        Returns:
            list: List of Method instances. Each one will be attached to the
                Block by calling block.add_method(method)
        """
        raise NotImplementedError("Controller subclass should implement this")
