from malcolm.parts.builtin.attributepart import AttributePart
from malcolm.core import method_also_takes
from malcolm.core.vmetas import NumberMeta


@method_also_takes(
    "initialValue", NumberMeta("float64", "Initial value of attribute"), 0.0,
)
class StringPart(AttributePart):
    def get_initial_value(self):
        return self.params.initialValue

    def create_meta(self, description, tags):
        return NumberMeta("float64", description=description, tags=tags)
