from collections import OrderedDict

from malcolm.core.notifier import Notifier
from malcolm.core.serializable import Serializable
from malcolm.core.request import Request
from malcolm.core.response import Response
from malcolm.core.attribute import Attribute
from malcolm.core.method import Method


class DummyLock(object):

    def acquire(self):
        pass

    def release(self):
        pass

    def __enter__(self):
        self.acquire()

    def __exit__(self, type_, value, traceback):
        self.release()
        return False


class LockRelease(object):
    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        self.lock.release()

    def __exit__(self, type_, value, traceback):
        self.lock.acquire()
        return False


@Serializable.register_subclass("malcolm:core/Block:1.0")
class Block(Notifier):
    """Object consisting of a number of Attributes and Methods"""

    def __init__(self, name):
        """
        Args:
            name (str): Block name e.g. "BL18I:ZEBRA1"
        """
        super(Block, self).__init__(name=name)
        self.name = name
        self.methods = OrderedDict()
        self.attributes = OrderedDict()
        self.lock = DummyLock()

    @property
    def endpoints(self):
        return list(self.attributes.keys()) + list(self.methods.keys())

    def add_attribute(self, attribute, notify=True):
        """Add an Attribute to the block and set the block as its parent"""
        self.add_child(attribute, self.attributes)
        self.on_changed([[attribute.name], attribute.to_dict()], notify)

    def add_method(self, method, notify=True):
        """Add a Method to the Block

        Args:
            method (Method): The Method object that has already been filled in
        """
        self.add_child(method, self.methods)
        self.on_changed([[method.name], method.to_dict()], notify)

    def add_child(self, attribute_or_method, d):
        """Add an Attribute or Method to the block and set the block as its
        parent, but don't notify"""
        child_name = attribute_or_method.name
        assert not hasattr(self, child_name), \
            "Attribute or Method %s already defined for Block %s" \
            % (child_name, self.name)
        setattr(self, child_name, attribute_or_method)
        d[child_name] = attribute_or_method
        attribute_or_method.set_parent(self)

    def _where_child_stored(self, child):
        if isinstance(child, Method):
            return self.methods
        elif isinstance(child, Attribute):
            return self.attributes

    def update(self, change):
        """Update block given a single change.
        Delegates to children update methods if possible.

        Args:
            change [[path], new value]: Path to changed element and new value
        """
        name = change[0][0]
        if hasattr(self, name):
            # sub-structure exists in block - delegate down
            # TODO: handle removal?
            getattr(self, name).update([change[0][1:], change[1]])
        else:
            # sub-structure does not exist - create and add
            if len(change[0]) > 1:
                raise ValueError("Missing substructure at %s" % name)
            child = Serializable.deserialize(name, change[1])
            d = self._where_child_stored(child)
            assert d is not None, \
                "Change %s deserialized to unknown object %s" % (change, child)
            self.add_child(child, d)

    def replace_children(self, children, notify=True):
        for method_name in self.methods:
            delattr(self, method_name)
        self.methods.clear()
        for attr_name in self.attributes:
            delattr(self, attr_name)
        self.attributes.clear()
        for child in children:
            d = self._where_child_stored(child)
            assert d is not None, \
                "Don't know how to add a child %s" % child
            self.add_child(child, d)
        self.on_changed([[], self.to_dict()], notify)

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
                response = self.methods[method_name].get_response(request)
            elif request.type_ == Request.PUT:
                attr_name = request.endpoint[-1]
                self.attributes[attr_name].put(request.value)
                self.attributes[attr_name].set_value(request.value)
                response = Response.Return(request.id_, request.context)
            self.parent.block_respond(response, request.response_queue)

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        overrides = {}
        for attribute_name, attribute in self.attributes.items():
            overrides[attribute_name] = attribute.to_dict()
        for method_name, method in self.methods.items():
            overrides[method_name] = method.to_dict()
        return super(Block, self).to_dict(**overrides)

    def lock_released(self):
        return LockRelease(self.lock)
