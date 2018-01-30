from malcolm.core import Part, config_tag, NumberMeta, PartRegistrar


class CounterPart(Part):
    """Defines a counter `Attribute` with zero and increment `Method` objects"""
    counter = None
    """Holds the current counter value"""

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        # Create writeable attribute for current counter value
        self.counter = NumberMeta(
            "float64", "The current value of the counter", tags=[config_tag()]
        ).create_attribute_model()
        registrar.add_attribute_model(
            "counter", self.counter, self.counter.set_value)
        registrar.add_method_model(self.zero)
        registrar.add_method_model(self.increment)

    def zero(self):
        """Zero the counter attribute"""
        self.counter.set_value(0)

    def increment(self):
        """Add one to the counter attribute"""
        self.counter.set_value(self.counter.value + 1)
