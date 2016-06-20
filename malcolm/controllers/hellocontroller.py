from malcolm.core.controller import Controller
from malcolm.core.method import Method, takes, returns
from malcolm.core.mapmeta import REQUIRED
from malcolm.core.stringmeta import StringMeta


class HelloController(Controller):
    @takes(StringMeta("name", "a name"), REQUIRED)
    @returns(StringMeta("greeting", "a greeting"), REQUIRED)
    def say_hello(self, args):
        """Says Hello to name

        Args:
            name (str): The name of the person to say hello to

        Returns:
            str: The greeting
        """
        return dict(greeting="Hello %s" % args["name"])
