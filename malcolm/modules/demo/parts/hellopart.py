from __future__ import print_function

import time

from annotypes import Anno, add_call_types

from malcolm.core import Part


with Anno("The name of the person to greet"):
    Name = str
with Anno("Time to wait before returning"):
    Sleep = float
with Anno("The manufactured greeting"):
    Greeting = str


class HelloPart(Part):
    """Defines greet and error `Method` objects on a `Block`"""

    def setup(self, registrar):
        registrar.add_method_model(self.greet)
        registrar.add_method_model(self.error)

    @add_call_types
    def greet(self, name, sleep):
        # type: (Name, Sleep) -> Greeting
        """Optionally sleep <sleep> seconds, then return a greeting to <name>"""
        print("Manufacturing greeting...")
        time.sleep(sleep)
        greeting = "Hello %s" % name
        return greeting

    def error(self):
        """Raise an error"""
        raise RuntimeError("You called method error()")
