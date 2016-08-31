import functools

from malcolm.core.attribute import Attribute
from malcolm.core.blockmeta import BlockMeta
from malcolm.core.elementmap import ElementMap
from malcolm.core.methodmeta import MethodMeta
from malcolm.core.request import Put, Post
from malcolm.core.response import Return, Error
from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/Block:1.0")
class Block(ElementMap):
    """Object consisting of a number of Attributes and Methods"""

    child_type_check = (Attribute, MethodMeta, BlockMeta)

    def __init__(self):
        super(Block, self).__init__()
        self._writeable_functions = {}

    def __setattr__(self, attr, value):
        if attr in self:
            child = self[attr]
            assert isinstance(child, Attribute), \
                "Expected Attribute, got %r" % (child,)
            func = self._writeable_functions[attr]
            func(child.meta, value)
        else:
            object.__setattr__(self, attr, value)

    def __getattr__(self, attr):
        if attr in self:
            child = self[attr]
            if isinstance(child, Attribute):
                return child.value
            else:
                func = self._writeable_functions[attr]
                return functools.partial(self._call_method, child, func)
        else:
            raise AttributeError(attr)

    def _call_method(self, method_meta, func, *args, **kwargs):
        for name, v in zip(method_meta.takes.elements, args):
            assert name not in kwargs, \
                "%s specified as positional and keyword args" % (name,)
            kwargs[name] = v
        return method_meta.call_post_function(func, kwargs, method_meta)

    def set_endpoint_data(self, name, value, notify=True):
        if name == "meta":
            assert isinstance(value, BlockMeta), \
                "Expected meta child to be BlockMeta, got %s" % (value,)
        else:
            assert isinstance(value, (Attribute, MethodMeta)), \
                "Expected %s child to be Attribute or MethodMeta, got %s" % \
                (name, value)
        super(Block, self).set_endpoint_data(name, value, notify)

    def set_writeable_functions(self, writeable_functions):
        self._writeable_functions = writeable_functions

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
            child = self[child_name]
            writeable_function = self._writeable_functions[child_name]
            result = child.handle_request(request, writeable_function)
            response = Return(request.id, request.context, result)
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Exception while handling %s" % request)
            response = Error(request.id, request.context, str(e))
        self._parent.block_respond(response, request.response_queue)

