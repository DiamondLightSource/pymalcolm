from __future__ import print_function

import time

from malcolm.core import Part, method_takes, method_returns, REQUIRED
from malcolm.modules.builtin.vmetas import StringMeta, NumberMeta


@method_takes(
    "name", StringMeta("Name of the Part within the controller"), REQUIRED)
class HelloPart(Part):
    """Defines greet and error `Method` objects on a `Block`"""
    def __init__(self, params):
        super(HelloPart, self).__init__(params.name)

    @method_takes(
        "name", StringMeta("a name"), REQUIRED,
        "sleep", NumberMeta("float64", "Time to wait before returning"), 0,
    )
    @method_returns(
        "greeting", StringMeta(description="a greeting"), REQUIRED
    )
    def greet(self, parameters, return_map):
        """Optionally sleep <sleep> seconds, then return a greeting to <name>"""
        print("Manufacturing greeting...")
        time.sleep(parameters.sleep)
        return_map.greeting = "Hello %s" % parameters.name
        return return_map

    @method_takes()
    def error(self):
        """Raise an error"""
        raise RuntimeError("You called method error()")
