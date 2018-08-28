from annotypes import Any

from malcolm.core import Part, PartRegistrar, StringMeta, Port, Alarm
from malcolm.modules import ca, builtin
from ..infos import cs_axis_names


class CompoundMotorCSPart(Part):
    """Defines a string `Attribute` representing the CS this compound motor
    is permanently assigned to by reading its motor record OUT link"""

    def __init__(self, name, rbv, group=None):
        # type: (ca.util.APartName, ca.util.ARbv, ca.util.AGroup) -> None
        super(CompoundMotorCSPart, self).__init__(name)
        meta = StringMeta("CS Axis")
        builtin.util.set_tags(meta, group=group, sink_port=Port.MOTOR)
        self.rbv = rbv
        self.attr = meta.create_attribute_model()
        self.catools = ca.util.CaToolsHelper.instance()
        # Subscriptions
        self.monitor = None
        # Hooks
        self.register_hooked(builtin.hooks.DisableHook, self.disconnect)
        self.register_hooked((builtin.hooks.InitHook,
                              builtin.hooks.DisableHook), self.reconnect)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.attr)

    def reconnect(self):
        # release old monitors
        self.disconnect()
        # make sure we can connect to the pvs
        ca_values = self.catools.checking_caget(
            [self.rbv], format=self.catools.FORMAT_CTRL)
        # Set initial value
        self._update_value(ca_values[0])
        # Setup monitor on rbv
        self.monitor = self.catools.camonitor(
            self.rbv, self._update_value, format=self.catools.FORMAT_TIME,
            notify_disconnect=True)

    def disconnect(self):
        if self.monitor is not None:
            self.monitor.close()
            self.monitor = None

    def _update_value(self, value):
        # type: (Any) -> None
        if not value.ok or value.severity != 0:
            self.attr.set_value(None, alarm=Alarm.invalid("Bad PV value"))
        else:
            # Split "@asyn(PORT,num)" into ["PORT", "num"]
            split = value.split("(")[1].rstrip(")").split(",")
            cs_port = split[0].strip()
            cs_axis = cs_axis_names[int(split[1].strip()) - 1]
            self.attr.set_value("%s,%s" % (cs_port, cs_axis))
