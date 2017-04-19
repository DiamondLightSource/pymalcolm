from malcolm.modules.builtin.parts.attributepart import AttributePart
from malcolm.core import method_also_takes
from malcolm.modules.builtin.vmetas import StringMeta


@method_also_takes(
    "initialValue", StringMeta("Initial value of attribute"), "",
)
class StringPart(AttributePart):
    def get_initial_value(self):
        return self.params.initialValue

    def create_meta(self, description, tags):
        return StringMeta(description=description, tags=tags)

