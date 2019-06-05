from annotypes import Anno

from malcolm.core import Part, PartRegistrar, StringMeta, Widget, APartName
from ..util import set_tags


with Anno("The URL that gives some help documentation for this Block"):
    AHelpUrl = str

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName


class HelpPart(Part):
    """Part representing a link to some help documentation for the GUI"""
    def __init__(self, help_url, name="help"):
        # type: (AHelpUrl, APartName) -> None
        super(HelpPart, self).__init__(name)
        meta = StringMeta("Help documentation for the Block")
        set_tags(meta, widget=Widget.HELP)
        self.attr = meta.create_attribute_model(help_url)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.attr)
