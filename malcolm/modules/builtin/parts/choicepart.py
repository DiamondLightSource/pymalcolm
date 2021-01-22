from enum import Enum
from typing import Sequence, Union

from annotypes import Anno, Array

from malcolm.core import AMetaDescription, APartName, ChoiceMeta, Part, PartRegistrar

from ..util import AConfig, AGroup, AWidget, AWriteable, set_tags

with Anno("Possible choices for this attribute"):
    AChoices = Union[Array[str]]
with Anno("Initial value of the created attribute"):
    AValue = str
UChoices = Union[AChoices, Sequence[Enum], Sequence[str], str]

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMetaDescription = AMetaDescription
AWriteable = AWriteable
AConfig = AConfig
AGroup = AGroup
AWidget = AWidget


class ChoicePart(Part):
    """Create a single choice Attribute on the Block"""

    def __init__(
        self,
        name: APartName,
        description: AMetaDescription,
        choices: UChoices,
        value: AValue,
        writeable: AWriteable = False,
        config: AConfig = 1,
        group: AGroup = None,
        widget: AWidget = None,
    ) -> None:
        super().__init__(name)
        meta = ChoiceMeta(description, choices)
        set_tags(meta, writeable, config, group, widget)
        self.attr = meta.create_attribute_model(value)
        self.writeable_func = self.attr.set_value if writeable else None

    def setup(self, registrar: PartRegistrar) -> None:
        registrar.add_attribute_model(self.name, self.attr, self.writeable_func)
