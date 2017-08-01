from malcolm.core import method_also_takes
from malcolm.modules.builtin.vmetas import StringMeta
from .attributepart import AttributePart


@method_also_takes(
    "initialValue", StringMeta("Initial value of attribute"), "",
)
class StringPart(AttributePart):
    def get_initial_value(self):
        return self.params.initialValue

    def create_meta(self, description, tags):
        return StringMeta(description=description, tags=tags)

