from cothread import catools

from malcolm.modules.builtin.controllers import StatefulController
from malcolm.core import method_takes, REQUIRED, Alarm, AlarmStatus, TimeStamp
from malcolm.modules.builtin.parts.attributepart import AttributePart
from malcolm.tags import widget_types, inport, port_types
from malcolm.modules.builtin.vmetas import StringMeta, ChoiceMeta, BooleanMeta


@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Desc of created attribute"), REQUIRED,
    "pv", StringMeta("Full pv of demand and default for rbv"), "",
    "rbv", StringMeta("Override for rbv"), "",
    "rbvSuff", StringMeta("Set rbv ro pv + rbv_suff"), "",
    "widget", ChoiceMeta("Widget type", [""] + widget_types), "",
    "inport", ChoiceMeta("Inport type", [""] + port_types), "",
    "config", BooleanMeta("Should this field be loaded/saved?"), False)
class CAPart(AttributePart):    
    def __init__(self, params):
        if not params.rbv and not params.pv:
            raise ValueError('Must pass pv or rbv')
        if not params.rbv:
            if params.rbvSuff:
                params.rbv = params.pv + params.rbvSuff
            else:
                params.rbv = params.pv
        # Camonitor subscription
        self.monitor = None
        super(CAPart, self).__init__(params)

    def get_writeable_func(self):
        if self.params.pv:
            writeable_func = self.caput
        else:
            writeable_func = None
        return writeable_func

    def create_tags(self):
        tags = super(CAPart, self).create_tags()
        if self.params.inport:
            tags.append(inport(self.params.inport, ""))
        return tags

    def get_datatype(self):
        raise NotImplementedError

    def set_initial_metadata(self, value):
        """Implement this to set some metadata on the attribute from the initial
        CA connect before the first update_value()"""
        pass

    @StatefulController.Init
    @StatefulController.Reset
    def reset(self, context=None):
        # release old monitor
        self.close_monitor()
        # make the connection in cothread's thread, use caget for initial value
        pvs = [self.params.rbv]
        if self.params.pv:
            pvs.append(self.params.pv)
        ca_values = catools.caget(
            pvs, format=catools.FORMAT_CTRL, datatype=self.get_datatype())
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]
        self.set_initial_metadata(ca_values[0])
        self.update_value(ca_values[0])
        # now setup monitor on rbv
        self.monitor = catools.camonitor(
            self.params.rbv, self.update_value,
            format=catools.FORMAT_TIME, datatype=self.get_datatype(),
            notify_disconnect=True, all_updates=True)

    @StatefulController.Disable
    def close_monitor(self, context=None):
        if self.monitor is not None:
            self.monitor.close()
            self.monitor = None

    def format_caput_value(self, value):
        self.log.info("caput -c -w 1000 %s %s", self.params.pv, value)
        return value

    def caput(self, value):
        value = self.format_caput_value(value)
        catools.caput(
            self.params.pv, value, wait=True, timeout=None,
            datatype=self.get_datatype())
        # now do a caget
        value = catools.caget(
            self.params.rbv,
            format=catools.FORMAT_TIME, datatype=self.get_datatype())
        self.update_value(value)

    def update_value(self, value):
        if not value.ok:
            alarm = Alarm.invalid("PV disconnected")
            ts = TimeStamp()
            value = None
        else:
            if value.severity:
                alarm = Alarm(severity=value.severity,
                              status=AlarmStatus.RECORD_STATUS,
                              message="PV in alarm state")
            else:
                alarm = Alarm.ok
            # We only have a raw_stamp attr on monitor, the initial
            # caget with CTRL doesn't give us a timestamp
            ts = TimeStamp(*getattr(value, "raw_stamp", (None, None)))
        self.attr.set_value_alarm_ts(value, alarm, ts)
