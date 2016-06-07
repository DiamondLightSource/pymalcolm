from collections import OrderedDict

from malcolm.core.mapmeta import MapMeta
from malcolm.core.monitorable import Monitorable


class Method(Monitorable):
    """Exposes a function with metadata for arguments and return values"""

    def __init__(self, name, description):
        super(Method, self).__init__(name=name)
        self.func = None
        self.description = description
        self.takes = None
        self.returns = None
        self.defaults = None

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

    def __call__(self, *args, **kwargs):
        """Call the exposed function using regular keyword argument parameters.
        Will validate the output against provided return parameters.
        """

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

    def handle_request(self, request):
        """Call exposed function using request parameters and respond with the
        result

        Args:
            request (Request): The request to handle
        """
        self.log_debug("Received request %s", request)
        try:
            result = self(**request.parameters)
        except Exception as error:
            self.log_debug("Error raised %s", error.message)
            message = "Method %s raised an error: %s" % (self.name, error.message)
            request.respond_with_error(message)
        else:
            self.log_debug("Returning result %s", result)
            request.respond_with_return(result)

    def to_dict(self):
        """Return ordered dictionary representing Method object."""
        serialized = OrderedDict()
        serialized["description"] = self.description
        serialized["takes"] = self.takes.to_dict()
        serialized["defaults"] = self.defaults.copy()
        serialized["returns"] = self.returns.to_dict()
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
        return method

    @staticmethod
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

            func.Method.takes = args

            return func
        return decorator

    @staticmethod
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

            func.Method.returns = args

            return func
        return decorator

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
            method = cls(name)
            method.set_function(func)
            func.Method = method

        return func
