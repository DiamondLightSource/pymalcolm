from annotypes import Any

from malcolm.compat import OrderedDict
from malcolm.core import Part, PartRegistrar, StringMeta, Port
from malcolm.modules import ca
from malcolm.modules.pmac.infos import cs_axis_names


def add_tag_if_not_there(meta, tag):
    # Add the outport tags
    old_tags = meta.tags
    new_tags = [t for t in old_tags if not t.startswith("outport:")]
    new_tags.append(tag)
    if old_tags != new_tags:
        meta.set_tags(new_tags)


class CSOutlinksPart(Part):
    """Defines a string `Attribute` for the CS Port name, and 10 outports
    for the axes A-Z and I for the axis assignments"""

    def __init__(self, name, rbv, group=None):
        # type: (ca.util.APartName, ca.util.ARbv, ca.util.AGroup) -> None
        super(CSOutlinksPart, self).__init__(name)
        self.meta = StringMeta("CS Port name")
        catools = ca.util.CaToolsHelper.instance()
        # This gives the port name
        self.caa = ca.util.CAAttribute(
            self.meta, catools.DBR_STRING, rbv=rbv, group=group,
            on_connect=self.update_tags)
        # These will be the "axis" outports
        self.axis_attrs = {}

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked)
        # Add 9 compound motor attributes
        for k in cs_axis_names + ["I"]:
            # Note no widget tag as we don't want it on the properties pane,
            # just the layout view
            v = StringMeta("Axis outport value %s" % k).create_attribute_model()
            self.axis_attrs[k] = v
            registrar.add_attribute_model(k.lower(), v)

    def update_tags(self, value):
        # type: (Any) -> None
        self.caa.attr.set_value(value)
        # Add the motor outport tags
        for k, v in self.axis_attrs.items():
            add_tag_if_not_there(v.meta, Port.MOTOR.outport_tag(
                connected_value="%s,%s" % (value, k)))
