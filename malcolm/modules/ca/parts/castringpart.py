from annotypes import Anno

from malcolm.core import Part, PartRegistrar, StringMeta, DEFAULT_TIMEOUT,\
    tags, AMri
from .. import util

with Anno("display type for port badge"):
    ABadgeDisplay = str

with Anno("name of attribute for badge value"):
    ABadgeAttr = str


class CAStringPart(Part):
    """Defines a string `Attribute` that talks to a DBR_STRING stringout PV"""

    def __init__(self,
                 name,  # type: util.APartName
                 description,  # type: util.AMetaDescription
                 pv="",  # type: util.APv
                 rbv="",  # type: util.ARbv
                 rbv_suffix="",  # type: util.ARbvSuffix
                 min_delta=0.05,  # type: util.AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: util.ATimeout
                 sink_port=None,  # type: util.ASinkPort
                 widget=None,  # type: util.AWidget
                 group=None,  # type: util.AGroup
                 config=True,  # type: util.AConfig
                 throw=True,  # type: util.AThrow
                 port_badge_mri=None,  # type: AMri
                 port_badge_attr=None,  # type: ABadgeAttr
                 port_badge_display=None,  # type: ABadgeDisplay
                 ):
        # type: (...) -> None
        super(CAStringPart, self).__init__(name)
        port_badge = None
        if port_badge_mri and port_badge_attr:
            port_badge = tags.badge_value_tag(mri=port_badge_mri,
                                 attribute_name=port_badge_attr,
                                 display=port_badge_display)
        self.caa = util.CAAttribute(
            StringMeta(description), util.catools.DBR_STRING, pv, rbv,
            rbv_suffix, min_delta, timeout,
            sink_port, widget, group, config, throw=throw,
            port_badge=port_badge)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked)

