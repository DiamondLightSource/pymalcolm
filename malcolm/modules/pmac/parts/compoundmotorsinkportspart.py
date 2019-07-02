from annotypes import Any

from malcolm.core import Part, PartRegistrar, StringMeta, Port, Alarm
from malcolm.modules import ca, builtin
from ..util import CS_AXIS_NAMES

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = ca.util.APartName
ARbv = ca.util.ARbv
AGroup = ca.util.AGroup


class CompoundMotorSinkPortsPart(Part):
    """Defines a string `Attribute` representing the CS this compound motor
    is permanently assigned to by reading its motor record OUT link"""

    def __init__(self, name, rbv, group=None):
        # type: (APartName, ARbv, AGroup) -> None
        super(CompoundMotorSinkPortsPart, self).__init__(name)
        meta = StringMeta("CS Axis")
        builtin.util.set_tags(meta, group=group, sink_port=Port.MOTOR)
        self.rbv = rbv
        self.attr = meta.create_attribute_model()
        # Subscriptions
        self.monitor = None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.attr)
        # Hooks
        registrar.hook(builtin.hooks.DisableHook, self.disconnect)
        registrar.hook((builtin.hooks.InitHook,
                        builtin.hooks.ResetHook), self.reconnect)

    def reconnect(self):
        # release old monitors
        self.disconnect()
        # make sure we can connect to the pvs
        ca_values = ca.util.assert_connected(ca.util.catools.caget(
            [self.rbv], format=ca.util.catools.FORMAT_CTRL))
        # Set initial value
        self._update_value(ca_values[0])
        # Setup monitor on rbv
        self.monitor = ca.util.catools.camonitor(
            self.rbv, self._update_value, format=ca.util.catools.FORMAT_TIME,
            notify_disconnect=True)

    def disconnect(self):
        if self.monitor is not None:
            self.monitor.close()
            self.monitor = None

    def _update_value(self, value):
        # type: (Any) -> None
        if not value.ok:
            self.attr.set_value(
                None, alarm=Alarm.disconnected("PV Disconnected"))
        else:
            # Split "@asyn(PORT,num)" into ["PORT", "num"]
            split = value.split("(")[1].rstrip(")").split(",")
            cs_port = split[0].strip()
            cs_axis = CS_AXIS_NAMES[int(split[1].strip()) - 1]
            self.attr.set_value("%s,%s" % (cs_port, cs_axis))
