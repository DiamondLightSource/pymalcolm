from collections import OrderedDict
from inspect import getdoc

from malcolm.core.monitorable import Monitorable
from malcolm.core.mapmeta import MapMeta, OPTIONAL, REQUIRED
from malcolm.core.response import Response


class Method(Monitorable):
    """Exposes a function with metadata for arguments and return values"""

    def __init__(self, name, description):
        super(Method, self).__init__(name=name)
        self.func = None
        self.description = description
        self.takes = None
        self.returns = None
        self.defaults = None
        self.writeable = True

    def set_function(self, func):
        """Set the function to expose.
        Function must return accept a dictionary of keyword arguments
        and return either a single value or dictionary of results.
        """
        self.func = func

    def set_function_takes(self, arg_meta, defaults=None):
        """Set the arguments and default values for the method

        Args:
            arg_meta (MapMeta): Arguments to the function
            default (dict): Default values for arguments (default None)
        """
        self.takes = arg_meta
        if defaults is not None:
            self.defaults = OrderedDict(defaults)
        else:
            self.defaults = OrderedDict()

    def set_function_returns(self, return_meta):
        """Set the return parameters for the method to validate against"""
        self.returns = return_meta

    def set_writeable(self, writeable):
        """Set writeable property to enable or disable calling method"""
        self.writeable = writeable
        self.on_changed([[["writeable"], writeable]])

    def __call__(self, *args, **kwargs):
        """Call the exposed function using regular keyword argument parameters.
        Will validate the output against provided return parameters.
        """

        if not self.writeable:
            raise ValueError("Can not call a method that is not writeable")

        # Assumes positional arguments represent arguments *before* any kw-args
        # in the ordered dictionary.
        for arg, arg_val in zip(self.takes.elements.keys(), args):
            kwargs[arg] = arg_val

        for arg in self.takes.elements:
            if arg not in kwargs.keys():
                if arg in self.defaults.keys():
                    kwargs[arg] = self.defaults[arg]
                elif arg in self.takes.required:
                    raise ValueError(
                        "Argument %s is required but was not provided" % arg)
        return_val = self.func(kwargs)
        if self.returns is not None:
            if return_val.keys() != self.returns.elements.keys():
                raise ValueError(
                    "Return result did not match specified return structure")
            for r_name, r_val in return_val.items():
                self.returns.elements[r_name].validate(r_val)
        return return_val

    def get_response(self, request):
        """Call exposed function using request parameters and respond with the
        result

        Args:
            request (Request): The request to handle
        """
        self.log_debug("Received request %s", request)
        try:
            result = self(**request.parameters)
        except Exception as error:
            # TODO: python3 no longer has error.message, but error.args[0]
            # seems the same. Is this always right?
            err_message = error.args[0]
            self.log_debug("Error raised %s", err_message)
            message = "Method %s raised an error: %s" % (self.name, err_message)
            return Response.Error(request.id_, request.context, message)
        else:
            self.log_debug("Returning result %s", result)
            return Response.Return(request.id_, request.context, value=result)

    def to_dict(self):
        """Return ordered dictionary representing Method object."""
        serialized = OrderedDict()
        serialized["description"] = self.description
        serialized["takes"] = self.takes.to_dict()
        serialized["defaults"] = self.defaults.copy()
        serialized["returns"] = self.returns.to_dict()
        serialized["writeable"] = self.writeable
        return serialized

    @classmethod
    def from_dict(cls, name, d):
        """Create a Method instance from the serialized version of itself

        Args:
            name (str): Method instance name
            d (dict): Something that self.to_dict() would create
        """
        method = cls(name, d["description"])
        takes = MapMeta.from_dict("takes", d["takes"])
        method.set_function_takes(takes, d["defaults"])
        returns = MapMeta.from_dict("returns", d["returns"])
        method.set_function_returns(returns)
        method.writeable = d["writeable"]
        return method

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

        takes_meta = MapMeta("takes")
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

        returns_meta = MapMeta("returns")
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
