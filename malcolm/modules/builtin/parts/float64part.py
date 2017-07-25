from malcolm.core import method_also_takes
from malcolm.modules.builtin.vmetas import NumberMeta
from .attributepart import AttributePart


@method_also_takes(
    "initialValue", NumberMeta("float64", "Initial value of attribute"), 0.0,
)
class Float64Part(AttributePart):
    def get_initial_value(self):
        return self.params.initialValue

    def create_meta(self, description, tags):
        return NumberMeta("float64", description=description, tags=tags)
