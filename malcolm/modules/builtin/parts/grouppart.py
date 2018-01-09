from malcolm.core import Part, Registrar, Widget
from malcolm.core.vmetas import ChoiceMeta
from ..util import set_tags, Name, Description


class GroupPart(Part):
    """Part representing a GUI group other Attributes attach to"""
    def __init__(self, name, description):
        # type: (Name, Description) -> None
        super(GroupPart, self).__init__(name)
        meta = ChoiceMeta(["expanded", "collapsed"], description)
        set_tags(meta, writeable=True, widget=Widget.GROUP)
        self.attr = meta.create_attribute_model("expanded")

    def setup(self, registrar):
        # type: (Registrar) -> None
        registrar.add_attribute_model(self.name, self.attr, self.attr.set_value)
