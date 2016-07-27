from collections import OrderedDict
from inspect import getdoc

from malcolm.core.serializable import Serializable
from malcolm.core.notifier import Notifier
from malcolm.core.response import Return, Error
from malcolm.core.map import Map
from malcolm.metas.mapmeta import MapMeta

OPTIONAL = object()
REQUIRED = object()


@Serializable.register_subclass("malcolm:core/Method:1.0")
class Method(Notifier):
    """Exposes a function with metadata for arguments and return values"""

    endpoints = ["takes", "defaults", "description", "tags", "writeable",
                 "returns"]

    def __init__(self, name, description=""):
        super(Method, self).__init__(name, description)
        self.func = None
        self.takes = MapMeta("takes", "Method arguments")
        self.returns = MapMeta("returns", "Method output structure")
        self.defaults = OrderedDict()
        self.writeable = True
        # List of state names that we are writeable in
        self.only_in = None
        self.tags = []
        self.label = name

    def set_function(self, func):
        """Set the function to expose.
        Function must return accept a dictionary of keyword arguments
        and return either a single value or dictionary of results.
        """
        self.func = func

    def set_takes(self, takes, defaults=None, notify=True):
        """Set the arguments and default values for the method

        Args:
            takes (MapMeta): Arguments to the function
            defaults (dict): Dict {str name: value} of default values for args
        """
        if defaults is not None:
            self.defaults = OrderedDict(defaults)
        else:
            self.defaults = OrderedDict()
        self.set_endpoint("takes", takes, notify)

    def set_returns(self, returns, notify=True):
        """Set the return parameters for the method to validate against"""
        self.set_endpoint("returns", returns, notify)

    def set_writeable(self, writeable, notify=True):
        """Set writeable property to enable or disable calling method"""
        self.set_endpoint("writeable", writeable, notify)

    def set_label(self, label, notify=True):
        self.set_endpoint("label", label, notify)

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

        for arg in self.takes.elements:
            if arg not in parameters_dict.keys():
                if arg in self.defaults.keys():
                    parameters_dict[arg] = self.defaults[arg]
                elif arg in self.takes.required:
                    raise ValueError(
                        "Argument %s is required but was not provided" % arg)

        parameters = Map(self.takes, parameters_dict)
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
            self.returns.validate(return_val)

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
            name = func.__name__
            description = getdoc(func)
            method = cls(name, description)
            func.Method = method

        return func


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

        takes_meta = MapMeta("takes", "Method arguments")
        defaults = OrderedDict()
        for index in range(0, len(args), 2):

            meta = args[index]
            is_required = args[index + 1] is REQUIRED
            takes_meta.add_element(meta, is_required)

            # If second of pair is not REQUIRED or OPTIONAL it is taken as
            # the default value
            if args[index + 1] not in [OPTIONAL, REQUIRED]:
                defaults[meta.name] = args[index + 1]

        func.Method.set_function_takes(takes_meta, defaults)

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

        returns_meta = MapMeta("returns", "Method output structure")
        for index in range(0, len(args), 2):

            if args[index + 1] not in [OPTIONAL, REQUIRED]:
                raise ValueError(
                    "Must specify if return value is REQUIRED or OPTIONAL")

            meta = args[index]
            is_required = args[index + 1] is REQUIRED
            returns_meta.add_element(meta, is_required)

        func.Method.set_function_returns(returns_meta)

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
