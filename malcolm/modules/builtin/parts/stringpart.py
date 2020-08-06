from annotypes import Anno

from malcolm.core import AMetaDescription, APartName, Part, PartRegistrar, StringMeta

from ..util import AConfig, AGroup, AWidget, AWriteable, set_tags

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

    def __init__(
        self,
        name: APartName,
        description: AMetaDescription,
        writeable: AWriteable = False,
        config: AConfig = 1,
        group: AGroup = None,
        widget: AWidget = None,
        value: AValue = "",
    ) -> None:
        super().__init__(name)
        meta = StringMeta(description)
        set_tags(meta, writeable, config, group, widget)
        self.attr = meta.create_attribute_model(value)
        self.writeable_func = self.attr.set_value if writeable else None

    def setup(self, registrar: PartRegistrar) -> None:
        registrar.add_attribute_model(self.name, self.attr, self.writeable_func)
