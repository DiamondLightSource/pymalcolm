from __future__ import print_function

from annotypes import Anno, add_call_types

from malcolm.core import Part, PartRegistrar, sleep as sleep_for

with Anno("The name of the person to greet"):
    AName = str
with Anno("Time to wait before returning"):
    ASleep = float
with Anno("The manufactured greeting"):
    AGreeting = str


class HelloPart(Part):
    """Defines greet and error `Method` objects on a `Block`"""

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(HelloPart, self).setup(registrar)
        registrar.add_method_model(self.greet)
        registrar.add_method_model(self.error)

    @add_call_types
    def greet(self, name, sleep=0):
        # type: (AName, ASleep) -> AGreeting
        """Optionally sleep <sleep> seconds, then return a greeting to <name>"""
        print("Manufacturing greeting...")
        sleep_for(sleep)
        greeting = "Hello %s" % name
        return greeting

    def error(self):
        """Raise an error"""
        raise RuntimeError("You called method error()")
