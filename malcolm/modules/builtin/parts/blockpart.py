from annotypes import Anno

from malcolm.core import Part, PartRegistrar, StringMeta, APartName, \
    AMetaDescription, Port
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


class BlockPart(Part):
    """Create a single string SinkPort for connecting to another Block"""
    def __init__(self,
                 name: APartName,
                 description: AMetaDescription,
                 writeable: AWriteable = True,
                 config: AConfig = 1,
                 group: AGroup = None,
                 widget: AWidget = None,
                 value: AValue = "",
                 ) -> None:
        super(BlockPart, self).__init__(name)
        meta = StringMeta(description)
        set_tags(meta, writeable, config, group, widget, sink_port=Port.BLOCK)
        self.attr = meta.create_attribute_model(value)
        self.writeable_func = self.attr.set_value if writeable else None

    def setup(self, registrar: PartRegistrar) -> None:
        registrar.add_attribute_model(self.name, self.attr, self.writeable_func)
