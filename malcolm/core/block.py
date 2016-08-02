from collections import OrderedDict

from malcolm.core.notifier import Notifier
from malcolm.core.serializable import Serializable
from malcolm.core.request import Put, Post
from malcolm.core.response import Return
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

    def __init__(self):
        self.methods = OrderedDict()
        self.attributes = OrderedDict()
        self.lock = DummyLock()

    @property
    def endpoints(self):
        return list(self.attributes.keys()) + list(self.methods.keys())

    def add_attribute(self, child_name, attribute, notify=True):
        """Add an Attribute to the block and set the block as its parent"""
        self.add_child(child_name, attribute, self.attributes)
        self.on_changed([[attribute.name], attribute.to_dict()], notify)

    def add_method(self, child_name, method, notify=True):
        """Add a Method to the Block

        Args:
            method (Method): The Method object that has already been filled in
        """
        self.add_child(child_name, method, self.methods)
        self.on_changed([[method.name], method.to_dict()], notify)

    def add_child(self, child_name, attribute_or_method, d):
        """Add an Attribute or Method to the block and set the block as its
        parent, but don't notify"""
        assert not hasattr(self, child_name), \
            "Attribute or Method %s already defined for Block %s" \
            % (child_name, self.name)
        setattr(self, child_name, attribute_or_method)
        d[child_name] = attribute_or_method
        attribute_or_method.set_parent(self, child_name)

    def _where_child_stored(self, child):
        if isinstance(child, Method):
            return self.methods
        elif isinstance(child, Attribute):
            return self.attributes

    def handle_change(self, change):
        """
        Set a given attribute to a new value
        Args:
            change(tuple): Attribute path and value e.g. (["value"], 5)
        """
        endpoint, value = change
        child_name = endpoint[0]
        if not hasattr(self, child_name):
            # Child doesn't exist, create it
            if len(endpoint) > 1:
                raise ValueError("Missing substructure at %s" % child_name)
            child_cls = Serializable.lookup_subclass(value)
            child = child_cls.from_dict(child_name, value)
            d = self._where_child_stored(child)
            assert d is not None, \
                "Change %s deserialized to unknown object %s" % (change, child)
            self.add_child(child, d)
        else:
            # Let super class set child attr
            super(Block, self).handle_change(change)

    def replace_children(self, children, notify=True):
        for method_name in self.methods:
            delattr(self, method_name)
        self.methods.clear()
        for attr_name in self.attributes:
            delattr(self, attr_name)
        self.attributes.clear()
        for name, child in children.items():
            d = self._where_child_stored(child)
            assert d is not None, \
                "Don't know how to add a child %s" % child
            self.add_child(name, child, d)
        self.on_changed([[], self.to_dict()], notify)

    def notify_subscribers(self):
        if hasattr(self, "parent"):
            self.parent.notify_subscribers(self.name)

    def handle_request(self, request):
        """
        Process the request depending on the type

        Args:
            request(Request): Request object specifying action
        """
        self.log_debug("Received request %s", request)
        assert isinstance(request, Post) or isinstance(request, Put), \
            "Expected Post or Put request, received %s" % request.typeid
        with self.lock:
            if isinstance(request, Post):
                if len(request.endpoint) != 2:
                    raise ValueError("POST endpoint requires 2 part endpoint")
                method_name = request.endpoint[1]
                response = self.methods[method_name].get_response(request)
            elif isinstance(request, Put):
                attr_name = request.endpoint[1]
                if len(request.endpoint) != 3:
                    raise ValueError("PUT endpoint requires 3 part endpoint")
                assert request.endpoint[2] == "value", \
                    "Can only put to an attribute value"
                self.attributes[attr_name].put(request.value)
                self.attributes[attr_name].set_value(request.value)
                response = Return(request.id_, request.context)
            self.parent.block_respond(response, request.response_queue)


    def lock_released(self):
        return LockRelease(self.lock)
