from annotypes import Anno

from malcolm.core import DEFAULT_TIMEOUT, AMri, Part, PartRegistrar, StringMeta, tags

from .. import util

with Anno("display type for port badge"):
    ABadgeDisplay = str

with Anno("name of attribute for badge value"):
    ABadgeAttr = str


class CAStringPart(Part):
    """Defines a string `Attribute` that talks to a DBR_STRING stringout PV"""

    def __init__(
        self,
        name: util.APartName,
        description: util.AMetaDescription,
        pv: util.APv = "",
        rbv: util.ARbv = "",
        rbv_suffix: util.ARbvSuffix = "",
        min_delta: util.AMinDelta = 0.05,
        timeout: util.ATimeout = DEFAULT_TIMEOUT,
        sink_port: util.ASinkPort = None,
        widget: util.AWidget = None,
        group: util.AGroup = None,
        config: util.AConfig = True,
        throw: util.AThrow = True,
        port_badge_mri: AMri = None,
        port_badge_attr: ABadgeAttr = None,
        port_badge_display: ABadgeDisplay = None,
    ) -> None:
        super().__init__(name)
        port_badge = None
        if port_badge_mri and port_badge_attr and port_badge_display:
            port_badge = tags.badge_value_tag(
                mri=port_badge_mri,
                attribute_name=port_badge_attr,
                display=port_badge_display,
            )
        self.caa = util.CAAttribute(
            StringMeta(description),
            util.catools.DBR_STRING,
            pv,
            rbv,
            rbv_suffix,
            min_delta,
            timeout,
            sink_port,
            widget,
            group,
            config,
            throw=throw,
            port_badge=port_badge,
        )

    def setup(self, registrar: PartRegistrar) -> None:
        self.caa.setup(registrar, self.name, self.register_hooked)
