import functools
from collections import OrderedDict

from malcolm.core.monitorable import Monitorable
from malcolm.core.serializable import Serializable, serialize_object
from malcolm.core.request import Put, Post
from malcolm.core.response import Return, Error
from malcolm.core.blockmeta import BlockMeta
from malcolm.core.attribute import Attribute
from malcolm.core.methodmeta import MethodMeta


@Serializable.register_subclass("malcolm:core/Block:1.0")
class Block(Monitorable):
    """Object consisting of a number of Attributes and Methods"""

    def __init__(self):
        self._writeable_functions = OrderedDict()
        self.children = OrderedDict()

    @property
    def endpoints(self):
        return list(self.children)

    def get_endpoint(self, endpoint):
        return self.children[endpoint]

    def __getitem__(self, key):
        return self.children[key]

    def __setattr__(self, attr, value):
        if hasattr(self, "children") and attr in self.children:
            child = self.children[attr]
            assert isinstance(child, Attribute), \
                "Expected Attribute, got %r" (child,)
            func = self._writeable_functions[attr]
            func(child, value)
        else:
            object.__setattr__(self, attr, value)

    def __getattr__(self, attr):
        if attr != "children" and hasattr(self, "children") \
                and attr in self.children:
            child = self.children[attr]
            if isinstance(child, Attribute):
                return child.value
            else:
                func = self._writeable_functions[attr]
                return functools.partial(self._call_method, child, func)
        else:
            raise AttributeError(attr)

    def _call_method(self, methodmeta, func, *args, **kwargs):
        for name, v in zip(methodmeta.takes.elements, args):
            assert name not in kwargs, \
                "%s specified as positional and keyword args" % (name,)
            kwargs[name] = v
        return methodmeta.call_post_function(func, kwargs)

    def set_children(self, children, writeable_functions={}):
        """Set the child objects"""
        assert isinstance(children, dict), \
            "Expected dict, got %r" % children
        for name, child in children.items():
            assert name != "children", "Block child can't be called children"
            if name == "meta":
                assert isinstance(child, BlockMeta), \
                    "Child called meta should be a BlockMeta, got %r" \
                    % (child,)
            else:
                assert isinstance(child, (Attribute, MethodMeta)), \
                    "Expected %s to be Attribute or MethodMeta, got %r" \
                    % (name, child)
        self._writeable_functions = OrderedDict()
        self.children = children
        for name, child in self.children.items():
            child.set_parent(self, name)
            if name in writeable_functions:
                self._writeable_functions[name] = writeable_functions[name]
        self.report_changes([[], serialize_object(self)])

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
        try:
            assert isinstance(request, Post) or isinstance(request, Put), \
                "Expected Post or Put request, received %s" % request.typeid
            child_name = request.endpoint[1]
            child = self.children[child_name]
            writeable_function = self._writeable_functions[child_name]
            result = child.handle_request(request, writeable_function)
            response = Return(request.id_, request.context, result)
        except Exception as e:
            self.log_exception("Exception while handling %s" % request)
            response = Error(request.id_, request.context, str(e))
        self.parent.block_respond(response, request.response_queue)

