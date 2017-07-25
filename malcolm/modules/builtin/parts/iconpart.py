from malcolm.core import method_takes, create_class_params
from malcolm.modules.builtin.vmetas import StringMeta
from .attributepart import AttributePart


@method_takes(
    "svg", StringMeta("If given, path to svg for initial value"), "")
class IconPart(AttributePart):
    """Part representing a the icon a GUI should display"""
    def __init__(self, params):
        try:
            with open(params.svg) as f:
                self.svg_text = f.read()
        except IOError:
            self.svg_text = "<svg/>"
        params = create_class_params(
            super(IconPart, self), name="icon",
            description="SVG icon for Block", widget="icon", writeable=False,
            config=False)
        super(IconPart, self).__init__(params)

    def get_initial_value(self):
        return self.svg_text

    def create_meta(self, description, tags):
        return StringMeta(description=description, tags=tags)
