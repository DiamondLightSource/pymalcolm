from collections import OrderedDict
import inspect

from malcolm.compat import base_string
from malcolm.core.map import Map
from malcolm.core.mapmeta import MapMeta
from malcolm.core.monitorable import NO_VALIDATE
from malcolm.core.response import Return, Error
from malcolm.core.serializable import Serializable
from malcolm.core.meta import Meta

OPTIONAL = object()
REQUIRED = object()


@Serializable.register_subclass("malcolm:core/Method:1.0")
class Method(Meta):
    """Exposes a function with metadata for arguments and return values"""

    endpoints = ["takes", "defaults", "description", "tags", "writeable",
                 "label", "returns"]

    def __init__(self, description="", tags=None, writeable=True, label=""):
        super(Method, self).__init__(description, tags, writeable, label)
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

    def __call__(self, *args, **kwargs):
        """Call the exposed function using regular keyword argument parameters.
        Will validate the output against provided return parameters.
        """
        # Assumes positional arguments represent arguments *before* any kw-args
        # in the ordered dictionary.
        for arg, arg_val in zip(self.takes.elements.keys(), args):
            kwargs[arg] = arg_val

        return self.call_function(kwargs)

    def call_function(self, parameters_dict):
        """
        Validate function parameters, call function and validate the response

        Args:
            parameters_dict(dict): Dictionary of parameter names and values

        Returns:
            Map: Return values
        """

        if not self.writeable:
            raise ValueError("Cannot call a method that is not writeable")

        for arg in self.defaults:
            if arg not in parameters_dict.keys():
                parameters_dict[arg] = self.defaults[arg]

        parameters = Map(self.takes, parameters_dict)
        parameters.check_valid()
        expected_response = Map(self.returns)

        if len(self.takes.elements) > 0:
            if len(self.returns.elements) > 0:
                return_val = self.func(parameters, expected_response)
            else:
                return_val = self.func(parameters)
        else:
            if len(self.returns.elements) > 0:
                return_val = self.func(expected_response)
            else:
                return_val = self.func()

        if len(self.returns.elements) > 0:
            return_val = Map(self.returns, return_val)
            return_val.check_valid()

        return return_val

    def get_response(self, request):
        """Call exposed function using request parameters and respond with the
        result

        Args:
            request (Request): The request to handle
        """
        self.log_debug("Received request %s", request)
        try:
            try:
                parameters = request.parameters
                if parameters is None:
                    parameters = {}
            except AttributeError:
                parameters = {}
            if "typeid" in parameters:
                parameters.pop("typeid")
            result = self.call_function(parameters)
        except Exception as error:
            err_message = str(error)
            self.log_exception("Error raised %s", err_message)
            message = "Method %s raised an error: %s" % (self.name, err_message)
            return Error(request.id_, request.context, message)
        else:
            self.log_debug("Returning result %s", result)
            return Return(request.id_, request.context, value=result)

    @classmethod
    def wrap_method(cls, func):
        """
        Checks if a function already has a Method implementation of itself and
        if it does not, creates one.

        Args:
            func: Function to wrap

        Returns:
            function: Function with Method instance of itself as an attribute
        """

        if not hasattr(func, "Method"):
            description = getdoc(func) or ""
            method = cls(description)
            func.Method = method

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

    # Setup the takes MapMeta and attach it to the function's Method
    meta = MapMeta()
    meta.set_elements(elements)
    meta.set_required(required)
    return meta, defaults


def takes(*args):
    """
    Checks if function has a Method representation, calls wrap_method to
    create one if it doesn't and then adds the takes attribute to it
    from *args

    Args:
        *args(list): List of form: [*Meta, REQUIRED/OPTIONAL, *Meta,
        REQUIRED/OPTIONAL]

    Returns:
        function: Updated function
    """

    def decorator(func):

        if not hasattr(func, "Method"):
            Method.wrap_method(func)

        takes_meta, defaults = _prepare_map_meta(args, allow_defaults=True)

        func.Method.set_takes(takes_meta)
        func.Method.set_defaults(defaults)
        return func

    return decorator


def returns(*args):
    """
    Checks if function has a Method representation, calls wrap_method to
    create one if it doesn't and then adds the returns attribute to it
    from *args

    Args:
        *args(list): List of form: [*Meta, REQUIRED/OPTIONAL, *Meta,
        REQUIRED/OPTIONAL]

    Returns:
        function: Updated function
    """

    def decorator(func):

        if not hasattr(func, "Method"):
            Method.wrap_method(func)

        returns_meta, _ = _prepare_map_meta(args, allow_defaults=False)

        func.Method.set_returns(returns_meta)
        return func

    return decorator

def only_in(*states):
    """
    Checks if function has a Method representation, calls wrap_method to
    create one if it doesn't and then adds only_in to it from *states

    Args:
        *args(list): List of state names, like DefaultStateMachine.RESETTING

    Returns:
        function: Updated function
    """
    def decorator(func):

        if not hasattr(func, "Method"):
            Method.wrap_method(func)

        func.Method.only_in = states

        return func
    return decorator


def get_method_decorated(instance):
    members = [value[1] for value in
                inspect.getmembers(instance, predicate=inspect.ismethod)]
    for member in members:
        if hasattr(member, "Method"):
            yield member
