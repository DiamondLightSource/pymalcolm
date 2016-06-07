from malcolm.core.controller import Controller
from malcolm.core.method import Method
from malcolm.core.mapmeta import MapMeta
from malcolm.core.stringmeta import StringMeta


class HelloController(Controller):
    def say_hello(self, args):
        """Says Hello to name

        Args:
            name (str): The name of the person to say hello to

        Returns:
            str: The greeting
        """
        return dict(greeting="Hello %s" % args["name"])

    def create_methods(self):
        """Create a Method wrapper for say_hello and return it"""
        method = Method("say_hello")
        method.set_function(self.say_hello)
        takes = MapMeta("takes")
        takes.add_element(StringMeta("name"))
        method.set_function_takes(takes)
        returns = MapMeta("returns")
        returns.add_element(StringMeta("greeting"))
        method.set_function_returns(returns)
        yield method
