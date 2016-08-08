from malcolm.core.vmetas import StringMeta
from malcolm.core import Controller, method_takes, method_returns, REQUIRED


@method_takes()
class HelloController(Controller):
    @method_takes("name", StringMeta(description="a name"), REQUIRED)
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
        return return_map
