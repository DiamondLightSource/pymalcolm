from annotypes import Anno, add_call_types

from malcolm.core import Part, PartRegistrar
from malcolm.core import sleep as sleep_for

with Anno("The name of the person to greet"):
    AName = str
with Anno("Time to wait before returning"):
    ASleep = float
with Anno("The manufactured greeting"):
    AGreeting = str


class HelloPart(Part):
    """Defines greet and error `Method` objects on a `Block`"""

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        registrar.add_method_model(self.greet)
        registrar.add_method_model(self.error)

    @add_call_types
    def greet(self, name: AName, sleep: ASleep = 0) -> AGreeting:
        """Optionally sleep <sleep> seconds, then return a greeting to <name>"""
        print("Manufacturing greeting...")
        sleep_for(sleep)
        greeting = "Hello %s" % name
        return greeting

    def error(self):
        """Raise an error"""
        raise RuntimeError("You called method error()")
