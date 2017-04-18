from malcolm.core import method_takes, Part, REQUIRED
from malcolm.modules.builtin.vmetas import NumberMeta, StringMeta


@method_takes(
    "name", StringMeta("Name of the Part within the controller"), REQUIRED)
class CounterPart(Part):
    # Attribute for the counter_block value
    counter = None

    def __init__(self, params):
        super(CounterPart, self).__init__(params.name)

    def create_attributes(self):
        self.counter = NumberMeta("float64", "A counter").create_attribute()
        yield "counter", self.counter, self.counter.set_value

    @method_takes()
    def zero(self):
        """Zero the counter_block attribute"""
        self.counter.set_value(0)

    @method_takes()
    def increment(self):
        """Add one to the counter_block attribute"""
        self.counter.set_value(self.counter.value + 1)

