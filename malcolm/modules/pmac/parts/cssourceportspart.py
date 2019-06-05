from annotypes import Any

from malcolm.core import Part, PartRegistrar, StringMeta, Port
from malcolm.modules import ca
from ..util import CS_AXIS_NAMES

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = ca.util.APartName
ARbv = ca.util.ARbv
AGroup = ca.util.AGroup


class CSSourcePortsPart(Part):
    """Defines a string `Attribute` for the CS Port name, and 10 Source Ports
    for the axes A-Z and I for the axis assignments"""

    def __init__(self, name, rbv, group=None):
        # type: (APartName, ARbv, AGroup) -> None
        super(CSSourcePortsPart, self).__init__(name)
        self.meta = StringMeta("CS Port name")
        # This gives the port name
        self.caa = ca.util.CAAttribute(
            self.meta, ca.util.catools.DBR_STRING, rbv=rbv, group=group,
            on_connect=self.update_tags)
        # These will be the "axis" Source Ports
        self.axis_attrs = {}

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked)
        # Add 9 compound motor attributes
        for k in CS_AXIS_NAMES + ["I"]:
            # Note no widget tag as we don't want it on the properties pane,
            # just the layout view
            v = StringMeta(
                "Axis Source Port value %s" % k
            ).create_attribute_model()
            self.axis_attrs[k] = v
            registrar.add_attribute_model(k.lower(), v)

    def update_tags(self, value):
        # type: (Any) -> None
        self.caa.attr.set_value(value)
        # Add the motor Source Port tags
        for k, v in self.axis_attrs.items():
            # Add the Source Port tags
            old_tags = v.meta.tags
            new_tags = Port.MOTOR.with_source_port_tag(
                old_tags, connected_value="%s,%s" % (value, k))
            if old_tags != new_tags:
                v.meta.set_tags(new_tags)
