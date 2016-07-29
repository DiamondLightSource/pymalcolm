from malcolm.metas import StringMeta
from malcolm.core.controller import Controller
from malcolm.core.method import takes, returns, REQUIRED


@takes()
class HelloController(Controller):
    @takes("name", StringMeta(description="a name"), REQUIRED)
    @returns("greeting", StringMeta(description="a greeting"), REQUIRED)
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
