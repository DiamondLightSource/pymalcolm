from malcolm.core import Attribute, method_takes, Part
from malcolm.core.vmetas import NumberMeta
from malcolm.controllers.builtin import DefaultController


@method_takes()
class CounterPart(Part):
    # Attribute for the counter value
    counter = None

    def create_attributes(self):
        self.counter = Attribute(NumberMeta("uint32", "A counter"), 0)
        yield ("counter", self.counter, self.counter.set_value)

    @method_takes()
    def zero(self):
        self.counter.set_value(0)

    @method_takes()
    def increment(self):
        self.counter.set_value(self.counter.value + 1)
