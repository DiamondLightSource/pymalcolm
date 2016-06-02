from collections import OrderedDict

from malcolm.core.loggable import Loggable


class Block(Loggable):
    """Object consisting of a number of Attributes and Methods"""

    def __init__(self, name):
        """
        Args:
            name (str): Block name e.g. "BL18I:ZEBRA1"
        """
        super(Block, self).__init__(logger_name=name)
        self.name = name
        self._methods = OrderedDict()

    def add_method(self, method):
        """Add a Method to the Block

        Args:
            method (Method): The Method object that has already been filled in
        """
        assert method.name not in self._methods, \
            "Method %s already defined for Block %s" % (method.name, self.name)
        self._methods[method.name] = method
        setattr(self, method.name, method)

    def handle_request(self, request):
        method_name = request.id.method
        response = self._methods[method_name].handle_request(request)

        return response

    def to_dict(self):

        d = OrderedDict()

        method_dict = OrderedDict()
        for method_name, method in self._methods.items():
            method_dict[method_name] = method.to_dict()
        d['methods'] = method_dict

        return d
