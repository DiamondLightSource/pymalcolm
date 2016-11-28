from __future__ import print_function
import time

from malcolm.core import Part, method_takes, method_returns, REQUIRED
from malcolm.core.vmetas import StringMeta, NumberMeta


class HelloPart(Part):
    @method_takes(
        "name", StringMeta("a name"), REQUIRED,
        "sleep", NumberMeta("float64", "Time to wait before returning"), 0,
    )
    @method_returns("greeting", StringMeta(description="a greeting"), REQUIRED)
    def greet(self, parameters, return_map):
        """Optionally sleep <sleep> seconds, then return a greeting to <name>"""
        print("Manufacturing greeting...")
        time.sleep(parameters.sleep)
        return_map.greeting = "Hello %s" % parameters.name
        return return_map

