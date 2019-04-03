from malcolm.core import Part, config_tag, NumberMeta, PartRegistrar, \
    Widget, AttributeModel


class CounterPart(Part):
    """Defines a counter `Attribute` with zero and increment `Method` objects"""

    #: Writeable Attribute holding the current counter value
    counter = None  # type: AttributeModel
    #: Writeable Attribute holding the amount to increment() by
    delta = None  # type: AttributeModel

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(CounterPart, self).setup(registrar)
        # Add some Attribute and Methods to the Block
        self.counter = NumberMeta(
            "float64", "The current value of the counter",
            tags=[config_tag(), Widget.TEXTINPUT.tag()]
        ).create_attribute_model()
        registrar.add_attribute_model(
            "counter", self.counter, self.counter.set_value)

        self.delta = NumberMeta(
            "float64", "The amount to increment() by",
            tags=[config_tag(), Widget.TEXTINPUT.tag()]
        ).create_attribute_model(initial_value=1)
        registrar.add_attribute_model(
            "delta", self.delta, self.delta.set_value)

        registrar.add_method_model(self.zero)
        registrar.add_method_model(self.increment)

    def zero(self):
        """Zero the counter attribute"""
        self.counter.set_value(0)

    def increment(self):
        """Add delta to the counter attribute"""
        self.counter.set_value(self.counter.value + self.delta.value)
