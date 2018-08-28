from annotypes import Anno

from malcolm.core import Part, PartRegistrar, ChoiceMeta, Port, Alarm
from malcolm.modules import ca, builtin
from malcolm.modules.pmac.infos import cs_axis_names

with Anno("PV prefix for CSPort and CSAxis records"):
    APrefix = str


class RawMotorCSPart(Part):
    """Defines a string `Attribute` representing a asyn port that should be
    depicted as a Source Port on a Block"""

    def __init__(self, name, prefix, group=None):
        # type: (ca.util.APartName, APrefix, ca.util.AGroup) -> None
        super(RawMotorCSPart, self).__init__(name)
        self.pvs = [prefix + ":CsPort", prefix + ":CsAxis"]
        self.rbvs = [prefix + ":CsPort_RBV", prefix + ":CsAxis_RBV"]
        meta = ChoiceMeta("CS Axis")
        builtin.util.set_tags(
            meta, writeable=True, group=group, sink_port=Port.MOTOR)
        self.attr = meta.create_attribute_model()
        self.catools = ca.util.CaToolsHelper.instance()
        # Subscriptions
        self.monitors = []
        self.port = None
        self.axis = None
        self.port_choices = []
        # Hooks
        self.register_hooked(builtin.hooks.DisableHook, self.disconnect)
        self.register_hooked((builtin.hooks.InitHook,
                              builtin.hooks.ResetHook), self.reconnect)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.attr, self.caput)

    def reconnect(self):
        # release old monitors
        self.disconnect()
        # make sure we can connect to the pvs
        ca_values = self.catools.checking_caget(
            self.pvs + self.rbvs, format=self.catools.FORMAT_CTRL)
        # Set initial value
        self.port_choices = ca_values[0].enums
        choices = [""]
        for choice in self.port_choices[1:]:
            for axis in cs_axis_names + ["I"]:
                choices.append("%s,%s" % (choice, axis))
        self.attr.meta.set_choices(choices)
        self.port = self.port_choices[ca_values[2]]
        self._update_value(ca_values[3], 1)
        # Setup monitor on rbvs
        self.monitors = self.catools.camonitor(
            self.rbvs, self._update_value, format=self.catools.FORMAT_TIME,
            notify_disconnect=True)

    def disconnect(self):
        for monitor in self.monitors:
            monitor.close()
        self.monitors = []

    def _update_value(self, value, index):
        if index == 0:
            if not value.ok:
                self.port = None
            elif value == 0:
                self.port = ""
            else:
                self.port = self.port_choices[value]
        else:
            if value.ok and str(value) in cs_axis_names + ["I"]:
                self.axis = value
            else:
                self.axis = None
        if self.port is None or self.axis is None:
            # Bad value or PV disconnected
            self.attr.set_value(None, alarm=Alarm.invalid("Bad PV value"))
        elif self.port and self.axis:
            # Connected to a port
            self.attr.set_value("%s,%s" % (self.port, self.axis))
        else:
            # Not connected to a port
            self.attr.set_value("")

    def caput(self, value):
        if value:
            port, axis = value.split(",")
            port_index = self.port_choices.index(port)
        else:
            port_index = 0
            axis = ""
        self.catools.caput(self.pvs, (port_index, axis), wait=True)
        # now do a caget
        values = self.catools.caget(self.rbvs, format=self.catools.FORMAT_TIME)
        self.port = self.port_choices[values[0]]
        self._update_value(values[1], 1)
