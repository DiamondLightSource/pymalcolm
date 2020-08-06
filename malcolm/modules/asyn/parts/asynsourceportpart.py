from typing import Any

from annotypes import Anno

from malcolm.core import Part, PartRegistrar, Port, StringMeta
from malcolm.modules import ca

with Anno("Source Port type"):
    APortType = Port

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = ca.util.APartName
AMetaDescription = ca.util.AMetaDescription
ARbv = ca.util.ARbv
AGroup = ca.util.AGroup


class AsynSourcePortPart(Part):
    """Defines a string `Attribute` representing a asyn port that should be
    depicted as an Source Port on a Block"""

    def __init__(
        self,
        name: APartName,
        description: AMetaDescription,
        rbv: ARbv,
        port_type: APortType,
        group: AGroup = None,
    ) -> None:
        super().__init__(name)
        self.port_type = port_type
        self.meta = StringMeta(description)
        self.caa = ca.util.CAAttribute(
            self.meta,
            ca.util.catools.DBR_STRING,
            rbv=rbv,
            group=group,
            on_connect=self.update_tags,
        )

    def setup(self, registrar: PartRegistrar) -> None:
        self.caa.setup(registrar, self.name, self.register_hooked)

    def update_tags(self, value: Any) -> None:
        # Add the Source Port tags
        old_tags = self.meta.tags
        new_tags = self.port_type.with_source_port_tag(old_tags, connected_value=value)
        if old_tags != new_tags:
            self.meta.set_tags(new_tags)
