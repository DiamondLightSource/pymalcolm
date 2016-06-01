#!/bin/env dls-python
from collections import OrderedDict

from loggable import Loggable

class Method(Loggable):
    """Exposes a function with metadata for arguments and return values"""

    def __init__(self, name):
        self.name = name
        self.func = None
        self.takes = None
        self.returns = None
        self.defaults = None

    def set_function(self, func):
        """Set the function to expose.
        Function must return accept a dictionary of keyword arguments
        and return either a single value or dictionary of results.
        """
        self.func = func

    def set_function_takes(self, arg_meta, defaults = None):
        """Set the arguments and default values for the method

        Args:
            arg_meta (MapMeta): Arguments to the function
            default (dict): Default values for arguments (default None)
        """
        self.takes = arg_meta
        self.defaults = OrderedDict(defaults) if defaults is not None else OrderedDict()

    def set_function_returns(self, return_meta):
        """Set the return parameters for the method to validate against"""
        self.returns = return_meta

    def __call__(self, *args, **kwargs):
        """Call the exposed function using regular keyword argument parameters.
        Will validate the output against provided return parameters.
        """

        for arg in self.takes.elements:
            if arg not in kwargs.keys():
                if arg in self.defaults.keys():
                    kwargs[arg] = self.defaults[arg]
                elif arg in self.takes.required:
                    raise ValueError("Argument %s is required but was not provided" % arg)
        return_val = self.func(kwargs)
        if self.returns is not None:
            if return_val.keys() != self.returns.elements.keys():
                raise ValueError("Return result did not match specified return structure")
            for r_name, r_val in return_val.iteritems():
                self.returns.elements[r_name].validate(r_val)
        return return_val
