from malcolm.core import method_takes, Part, REQUIRED
from malcolm.modules.builtin.vmetas import NumberMeta, StringMeta
from malcolm.tags import config


@method_takes(
    "name", StringMeta("Name of the Part within the controller"), REQUIRED)
class CounterPart(Part):
    """Defines a counter `Attribute` with zero and increment `Method` objects"""
    #: `AttributeModel` that will hold the counter value
    counter = None

    def __init__(self, params):
        super(CounterPart, self).__init__(params.name)

    def create_attribute_models(self):
        # Create writeable attribute for current counter value
        meta = NumberMeta("float64", "A counter", tags=[config()])
        self.counter = meta.create_attribute_model()
        yield "counter", self.counter, self.counter.set_value

    @method_takes()
    def zero(self):
        """Zero the counter attribute"""
        self.counter.set_value(0)

    @method_takes()
    def increment(self):
        """Add one to the counter attribute"""
        self.counter.set_value(self.counter.value + 1)

