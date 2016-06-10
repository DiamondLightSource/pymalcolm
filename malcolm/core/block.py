from collections import OrderedDict

from malcolm.core.monitorable import Monitorable


class Block(Monitorable):
    """Object consisting of a number of Attributes and Methods"""

    def __init__(self, name):
        """
        Args:
            name (str): Block name e.g. "BL18I:ZEBRA1"
        """
        super(Block, self).__init__(name=name)
        self.name = name
        self._methods = OrderedDict()
        self._attributes = OrderedDict()

    def add_attribute(self, attribute):
        """Add an Attribute to the block and set the block as its parent"""

        assert attribute.name not in self._attributes, \
            "Attribute %s already defined for Block %s" \
            % (attribute.name, self.name)
        self._attributes[attribute.name] = attribute
        attribute.set_parent(self)
        setattr(self, attribute.name, attribute)
        self.on_changed([[[attribute.name], attribute.to_dict()]])

    def add_method(self, method):
        """Add a Method to the Block

        Args:
            method (Method): The Method object that has already been filled in
        """
        assert method.name not in self._methods, \
            "Method %s already defined for Block %s" % (method.name, self.name)
        self._methods[method.name] = method
        setattr(self, method.name, method)
        self.on_changed([[[method.name], method.to_dict()]])

    def handle_request(self, request):
        """
        Process the request depending on the type

        Args:
            request(Request): Request object specifying action
        """
        self.log_debug("Received request %s", request)
        if request.type_ == request.POST:
            method_name = request.endpoint[-1]
            self._methods[method_name].handle_request(request)
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

        for attribute_name, attribute in self._attributes.items():
            d[attribute_name] = attribute.to_dict()
        for method_name, method in self._methods.items():
            d[method_name] = method.to_dict()

        return d
