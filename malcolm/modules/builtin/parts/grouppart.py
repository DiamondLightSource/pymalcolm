from malcolm.core import Part, PartRegistrar, ChoiceMeta, APartName, \
    AMetaDescription, Widget
from ..util import set_tags

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMetaDescription = AMetaDescription


class GroupPart(Part):
    """Part representing a GUI group other Attributes attach to"""
    def __init__(self, name, description):
        # type: (APartName, AMetaDescription) -> None
        super(GroupPart, self).__init__(name)
        meta = ChoiceMeta(description, ["expanded", "collapsed"])
        set_tags(meta, writeable=True, widget=Widget.GROUP)
        self.attr = meta.create_attribute_model("expanded")

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.attr, self.attr.set_value)
