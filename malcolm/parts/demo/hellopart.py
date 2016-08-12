import time

from malcolm.core import Part, method_takes, method_returns, REQUIRED
from malcolm.core.vmetas import StringMeta, NumberMeta


@method_takes()
class HelloPart(Part):
    @method_takes(
        "name", StringMeta("a name"), REQUIRED,
        "sleep", NumberMeta("float64", "Time to wait before returning"), 0,
    )
    @method_returns("greeting", StringMeta(description="a greeting"), REQUIRED)
    def say_hello(self, parameters, return_map):
        """Says Hello to name

        Args:
            parameters(Map): The name of the person to say hello to
            return_map(Map): Return structure to complete and return

        Returns:
            Map: The greeting
        """

        return_map.greeting = "Hello %s" % parameters.name
        time.sleep(parameters.sleep)
        return return_map
