from annotypes import Anno

from malcolm.core import Part, PartRegistrar, StringMeta, APartName, \
    AMetaDescription
from ..util import set_tags, AWriteable, AConfig, AGroup, AWidget

with Anno("Initial value of the created attribute"):
    AValue = str

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMetaDescription = AMetaDescription
AWriteable = AWriteable
AConfig = AConfig
AGroup = AGroup
AWidget = AWidget


class StringPart(Part):
    """Create a single string Attribute on the Block"""
    def __init__(self,
                 name,  # type: APartName
                 description,  # type: AMetaDescription
                 writeable=False,  # type: AWriteable
                 config=1,  # type: AConfig
                 group=None,  # type: AGroup
                 widget=None,  # type: AWidget
                 value="",  # type: AValue
                 ):
        # type: (...) -> None
        super(StringPart, self).__init__(name)
        meta = StringMeta(description)
        set_tags(meta, writeable, config, group, widget)
        self.attr = meta.create_attribute_model(value)
        self.writeable_func = self.attr.set_value if writeable else None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.attr, self.writeable_func)
