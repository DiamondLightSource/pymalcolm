from malcolm.core import Part, AttributeModel, config_tag
from malcolm.core.vmetas import NumberMeta


class CounterPart(Part):
    """Defines a counter `Attribute` with zero and increment `Method` objects"""
    counter = None  # type: AttributeModel
    """Holds the current counter value"""

    def setup(self, registrar):
        # Create writeable attribute for current counter value
        meta = NumberMeta("float64", "A counter", tags=[config_tag()])
        attr = meta.create_attribute_model()
        self.counter = registrar.add_attribute_model(
            "counter", attr, attr.set_value)
        registrar.add_method_model(self.zero)
        registrar.add_method_model(self.increment)

    def zero(self):
        """Zero the counter attribute"""
        self.counter.set_value(0)

    def increment(self):
        """Add one to the counter attribute"""
        self.counter.set_value(self.counter.value + 1)
