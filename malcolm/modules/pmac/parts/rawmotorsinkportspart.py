from annotypes import Anno

from malcolm.core import Part, PartRegistrar, ChoiceMeta, Port, Alarm, \
    StringMeta
from malcolm.modules import ca, builtin
from ..util import CS_AXIS_NAMES

with Anno("PV prefix for CSPort and CSAxis records"):
    APvPrefix = str

# Pull re-used annotypes into our namespace in case we are subclassed
AGroup = ca.util.AGroup


class RawMotorSinkPortsPart(Part):
    """Defines a string `Attribute` representing a asyn port that should be
    depicted as a Source Port on a Block"""

    def __init__(self, pv_prefix, group=None):
        # type: (APvPrefix, ca.util.AGroup) -> None
        super(RawMotorSinkPortsPart, self).__init__("sinkPorts")
        self.pvs = [pv_prefix + ":CsPort", pv_prefix + ":CsAxis"]
        self.rbvs = [pv_prefix + ":CsPort_RBV", pv_prefix + ":CsAxis_RBV",
                     pv_prefix + ".OUT"]
        meta = ChoiceMeta("CS Axis")
        builtin.util.set_tags(
            meta, writeable=True, group=group, sink_port=Port.MOTOR)
        self.cs_attr = meta.create_attribute_model()
        meta = StringMeta("Parent PMAC Port name")
        builtin.util.set_tags(meta, group=group, sink_port=Port.MOTOR)
        self.pmac_attr = meta.create_attribute_model()
        # Subscriptions
        self.monitors = []
        self.port = None
        self.axis = None
        self.port_choices = []

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model("pmac", self.pmac_attr)
        registrar.add_attribute_model("cs", self.cs_attr, self.caput)
        # Hooks
        registrar.hook(builtin.hooks.DisableHook, self.disconnect)
        registrar.hook((builtin.hooks.InitHook,
                        builtin.hooks.ResetHook), self.reconnect)

    def reconnect(self):
        # release old monitors
        self.disconnect()
        # make sure we can connect to the pvs
        ca_values = ca.util.assert_connected(ca.util.catools.caget(
            self.pvs + self.rbvs, format=ca.util.catools.FORMAT_CTRL))
        # Set initial value
        self.port_choices = ca_values[0].enums
        choices = [""]
        for choice in self.port_choices[1:]:
            for axis in CS_AXIS_NAMES + ["I"]:
                choices.append("%s,%s" % (choice, axis))
        self.cs_attr.meta.set_choices(choices)
        self.port = self.port_choices[ca_values[2]]
        self._update_value(ca_values[3], 1)
        self._update_value(ca_values[4], 2)
        # Setup monitor on rbvs
        self.monitors = ca.util.catools.camonitor(
            self.rbvs, self._update_value, format=ca.util.catools.FORMAT_TIME,
            notify_disconnect=True)

    def disconnect(self):
        for monitor in self.monitors:
            monitor.close()
        self.monitors = []

    def _update_value(self, value, index):
        if index == 0:
            # Got CS Port
            if not value.ok:
                self.port = None
            elif value == 0:
                self.port = ""
            else:
                self.port = self.port_choices[value]
        elif index == 1:
            # Got CS Axis
            if value.ok and str(value) in CS_AXIS_NAMES + ["I"]:
                self.axis = value
            else:
                self.axis = None
        else:
            # Got PMAC Port name
            if value.ok:
                # Split "@asyn(PORT,num)" into ["PORT", "num"]
                split = value.split("(")[1].rstrip(")").split(",")
                self.pmac_attr.set_value(split[0].strip())
            else:
                self.pmac_attr.set_value(
                    None, alarm=Alarm.invalid("Bad PV value"))
        if self.port is None or self.axis is None:
            # Bad value or PV disconnected
            self.cs_attr.set_value(None, alarm=Alarm.invalid("Bad PV value"))
        elif self.port and self.axis:
            # Connected to a port
            self.cs_attr.set_value("%s,%s" % (self.port, self.axis))
        else:
            # Not connected to a port
            self.cs_attr.set_value("")

    def caput(self, value):
        if value:
            port, axis = value.split(",")
            port_index = self.port_choices.index(port)
        else:
            port_index = 0
            axis = ""
        ca.util.catools.caput(self.pvs, (port_index, axis), wait=True)
        # now do a caget
        values = ca.util.catools.caget(
            self.rbvs, format=ca.util.catools.FORMAT_TIME)
        self.port = self.port_choices[values[0]]
        self._update_value(values[1], 1)
