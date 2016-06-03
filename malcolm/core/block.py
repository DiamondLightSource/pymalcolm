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
        """
        Process the request depending on the type

        Args:
            request(Request): Request object specifying action
        """

        if request.type == request.POST:
            method_name = request.endpoint[-1]
            response = self._methods[method_name].handle_request(request)
            request.respond_with_return(response.to_dict())
        else:
            layer = self
            for next_link in request.endpoint[1:]:
                layer = getattr(layer, next_link)

            if hasattr(layer, "to_dict"):
                request.respond_with_return(layer.to_dict())
            else:
                request.respond_with_return(layer)

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = OrderedDict()

        method_dict = OrderedDict()
        for method_name, method in self._methods.items():
            method_dict[method_name] = method.to_dict()
        d['methods'] = method_dict

        return d
