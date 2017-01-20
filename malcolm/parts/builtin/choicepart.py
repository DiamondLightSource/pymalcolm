from malcolm.parts.builtin.attributepart import AttributePart
from malcolm.core import method_also_takes, REQUIRED
from malcolm.core.vmetas import ChoiceMeta, StringMeta, StringArrayMeta


@method_also_takes(
    "choices", StringArrayMeta("Possible choices for this attribute"), REQUIRED,
    "initialValue", StringMeta("Initial value of attribute"), REQUIRED,
)
class ChoicePart(AttributePart):
    def get_initial_value(self):
        return self.params.initialValue

    def create_meta(self, description, tags):
        return ChoiceMeta(
            choices=self.params.choices, description=description, tags=tags)
