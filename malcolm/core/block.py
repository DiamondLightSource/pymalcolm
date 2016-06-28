from collections import OrderedDict
from contextlib import contextmanager

from malcolm.core.serializable import Serializable
from malcolm.core.request import Request
from malcolm.core.response import Response

@contextmanager
def dummy_lock():
    yield

class LockRelease(object):
    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        self.lock.__exit__(None, None, None)

    def __exit__(self, type, value, traceback):
        self.lock.__enter__()
        return False

@Serializable.register("malcolm:core/Block:1.0")
class Block(Serializable):
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
        self.lock = dummy_lock()

    def add_attribute(self, attribute):
        """Add an Attribute to the block and set the block as its parent"""

        assert attribute.name not in self._attributes, \
            "Attribute %s already defined for Block %s" \
            % (attribute.name, self.name)
        self._attributes[attribute.name] = attribute
        attribute.set_parent(self)
        setattr(self, attribute.name, attribute)
        self.on_changed([[attribute.name], attribute.to_dict()])
        self.notify_subscribers()

    def add_method(self, method):
        """Add a Method to the Block

        Args:
            method (Method): The Method object that has already been filled in
        """
        assert method.name not in self._methods, \
            "Method %s already defined for Block %s" % (method.name, self.name)
        self._methods[method.name] = method
        setattr(self, method.name, method)
        self.on_changed([[method.name], method.to_dict()])
        self.notify_subscribers()

    def notify_subscribers(self):
        if self.parent is not None:
            self.parent.notify_subscribers(self.name)

    def handle_request(self, request):
        """
        Process the request depending on the type

        Args:
            request(Request): Request object specifying action
        """
        self.log_debug("Received request %s", request)
        assert request.type_ == Request.POST or request.type_ == Request.PUT, \
            "Expected Post or Put request, received %s" % request.type_
        with self.lock:
            if request.type_ == Request.POST:
                method_name = request.endpoint[-1]
                response = self._methods[method_name].get_response(request)
            elif request.type_ == Request.PUT:
                attr_name = request.endpoint[-1]
                self._attributes[attr_name].put(request.value)
                self._attributes[attr_name].set_value(request.value)
                response = Response.Return(request.id_, request.context)
            self.parent.block_respond(response, request.response_queue)

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = OrderedDict()

        for attribute_name, attribute in self._attributes.items():
            d[attribute_name] = attribute.to_dict()
        for method_name, method in self._methods.items():
            d[method_name] = method.to_dict()

        return d

    def lock_released(self):
        return LockRelease(self.lock)
