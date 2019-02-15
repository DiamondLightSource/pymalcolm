from annotypes import Anno

from malcolm.core import Part, PartRegistrar, StringMeta, Widget
from ..util import set_tags


with Anno("If given, path to svg for initial value"):
    ASvg = str


class IconPart(Part):
    """Part representing a the icon a GUI should display"""
    def __init__(self, svg=""):
        # type: (ASvg) -> None
        super(IconPart, self).__init__("icon")
        meta = StringMeta("SVG icon for the Block")
        set_tags(meta, widget=Widget.ICON)
        try:
            with open(svg) as f:
                svg_text = f.read()
        except IOError:
            svg_text = "<svg/>"
        self.attr = meta.create_attribute_model(svg_text)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.attr)
