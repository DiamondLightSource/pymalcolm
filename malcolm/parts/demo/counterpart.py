from malcolm.core import method_takes, Part
from malcolm.core.vmetas import NumberMeta


@method_takes()
class CounterPart(Part):
    # Attribute for the counter value
    counter = None

    def create_attributes(self):
        self.counter = NumberMeta("uint32", "A counter").make_attribute()
        yield "counter", self.counter, self.counter.set_value

    @method_takes()
    def zero(self):
        """Zero the counter attribute"""
        self.counter.set_value(0)

    @method_takes()
    def increment(self):
        """Add one to the counter attribute"""
        self.counter.set_value(self.counter.value + 1)
