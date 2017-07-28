from malcolm.core import method_takes, REQUIRED, create_class_params
from malcolm.modules.builtin.vmetas import StringMeta
from .attributepart import AttributePart


@method_takes(
    "initialValue", StringMeta("Initial value of Block label"), REQUIRED,
    "group", StringMeta("If given, which GUI group should we attach to"), "",
)
class LabelPart(AttributePart):
    """Part representing a the icon a GUI should display"""
    def __init__(self, params):
        self.initial_value = params.initialValue
        params = create_class_params(
            super(LabelPart, self), name="label",
            description="Label for created block", widget="textinput",
            group=params.group, writeable=True, config=True)
        super(LabelPart, self).__init__(params)

    def get_initial_value(self):
        self.controller.set_label(self.initial_value)
        return self.initial_value

    def create_meta(self, description, tags):
        return StringMeta(description=description, tags=tags)

    def get_writeable_func(self):
        return self.set_label

    def set_label(self, value):
        with self.controller.changes_squashed:
            self.controller.set_label(value)
            self.attr.set_value(value)
