from collections import OrderedDict
import inspect

from malcolm.compat import base_string
from malcolm.core.map import Map
from malcolm.core.mapmeta import MapMeta
from malcolm.core.request import Post
from malcolm.core.monitorable import NO_VALIDATE
from malcolm.core.response import Return, Error
from malcolm.core.serializable import Serializable
from malcolm.core.meta import Meta

OPTIONAL = object()
REQUIRED = object()


@Serializable.register_subclass("malcolm:core/MethodMeta:1.0")
class MethodMeta(Meta):
    """Exposes a function with metadata for arguments and return values"""

    endpoints = ["takes", "defaults", "description", "tags", "writeable",
                 "label", "returns"]

    def __init__(self, description="", tags=None, writeable=True, label=""):
        super(MethodMeta, self).__init__(description, tags, writeable, label)
        self.func = None
        self.set_takes(MapMeta())
        self.set_returns(MapMeta())
        self.defaults = OrderedDict()
        # List of state names that we are writeable in
        self.only_in = None

    def set_function(self, func):
        """Set the function to expose.
        """
        self.func = func

    def set_takes(self, takes, notify=True):
        """Set the arguments and default values for the method

        Args:
            takes (MapMeta): Arguments to the function
        """
        self.set_endpoint(MapMeta, "takes", takes, notify)

    def set_defaults(self, defaults, notify=True):
        """Set the default dict"""
        for k, v in defaults.items():
            assert isinstance(k, base_string), \
                "Expected string, got %s" % (k,)
            defaults[k] = self.takes.elements[k].validate(v)
        self.set_endpoint(NO_VALIDATE, "defaults", defaults, notify)

    def set_returns(self, returns, notify=True):
        """Set the return parameters for the method to validate against"""
        self.set_endpoint(MapMeta, "returns", returns, notify)

    def handle_request(self, request, post_function):
        self.log_debug("Received request %s", request)
        assert isinstance(request, Post), "Expected Post, got %r" % (request,)
        assert len(request.endpoint) == 2, "Can only Post to MethodMeta root"
        return self.call_post_function(post_function, request.parameters)

    def prepare_input_map(self, param_dict):
        params = Map(self.takes, self.defaults)
        if param_dict:
            params.update(param_dict)
        params.check_valid()
        return params

    def call_post_function(self, post_function, param_dict):
        need_params = bool(self.takes.elements)
        need_ret = bool(self.returns.elements)
        args = []
        # Prepare input map
        if need_params:
            params = self.prepare_input_map(param_dict)
            args.append(params)

        # Prepare output map
        if need_ret:
            ret = Map(self.returns)
            args.append(ret)

        self.log_debug("Calling with %s" % (args,))

        result = post_function(self, *args)
        if need_ret:
            result = Map(self.returns, result)
            result.check_valid()

        return result

    @classmethod
    def wrap_method(cls, func):
        """
        Checks if a function already has a MethodMeta implementation of itself and
        if it does not, creates one.

        Args:
            func: Function to wrap

        Returns:
            function: Function with MethodMeta instance of itself as an attribute
        """

        if not hasattr(func, "MethodMeta"):
            description = inspect.getdoc(func) or ""
            method = cls(description)
            func.MethodMeta = method

        return func


def _prepare_map_meta(args, allow_defaults):
    # prepare some data structures that will be used for the takes MapMeta
    defaults = OrderedDict()
    elements = OrderedDict()
    required = []
    for index in range(0, len(args), 3):
        # pick out 3 arguments
        name = args[index]
        meta = args[index + 1]
        default = args[index + 2]
        # store them in the right structures
        elements[name] = meta
        if default is REQUIRED:
            required.append(name)
        elif default is not OPTIONAL:
            assert allow_defaults, \
                "Defaults not allowed in this structure"
            defaults[name] = default

    # Setup the takes MapMeta and attach it to the function's MethodMeta
    meta = MapMeta()
    meta.set_elements(elements)
    meta.set_required(required)
    return meta, defaults


def takes(*args):
    """
    Checks if function has a MethodMeta representation, calls wrap_method to
    create one if it doesn't and then adds the takes attribute to it
    from *args

    Args:
        *args(list): List of form: [*Meta, REQUIRED/OPTIONAL, *Meta,
        REQUIRED/OPTIONAL]

    Returns:
        function: Updated function
    """

    def decorator(func):

        if not hasattr(func, "MethodMeta"):
            MethodMeta.wrap_method(func)

        takes_meta, defaults = _prepare_map_meta(args, allow_defaults=True)

        func.MethodMeta.set_takes(takes_meta)
        func.MethodMeta.set_defaults(defaults)
        return func

    return decorator


def returns(*args):
    """
    Checks if function has a MethodMeta representation, calls wrap_method to
    create one if it doesn't and then adds the returns attribute to it
    from *args

    Args:
        *args(list): List of form: [*Meta, REQUIRED/OPTIONAL, *Meta,
        REQUIRED/OPTIONAL]

    Returns:
        function: Updated function
    """

    def decorator(func):

        if not hasattr(func, "MethodMeta"):
            MethodMeta.wrap_method(func)

        returns_meta, _ = _prepare_map_meta(args, allow_defaults=False)

        func.MethodMeta.set_returns(returns_meta)
        return func

    return decorator


def only_in(*states):
    """
    Checks if function has a MethodMeta representation, calls wrap_method to
    create one if it doesn't and then adds only_in to it from *states

    Args:
        *args(list): List of state names, like DefaultStateMachine.RESETTING

    Returns:
        function: Updated function
    """
    def decorator(func):

        if not hasattr(func, "MethodMeta"):
            MethodMeta.wrap_method(func)

        func.MethodMeta.only_in = states

        return func
    return decorator


def get_method_decorated(instance):
    for name, member in inspect.getmembers(instance, inspect.ismethod):
        if hasattr(member, "MethodMeta"):
            yield name, member.MethodMeta, member
