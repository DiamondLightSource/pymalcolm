import time

from malcolm.modules.builtin.controllers import StatefulController
from malcolm.core import method_takes, REQUIRED, Alarm, AlarmStatus, TimeStamp
from malcolm.modules.builtin.parts.attributepart import AttributePart
from malcolm.tags import widget_types, inport, port_types
from malcolm.modules.builtin.vmetas import StringMeta, ChoiceMeta, \
    BooleanMeta, NumberMeta
from .catoolshelper import CaToolsHelper


@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Description of created attribute"), REQUIRED,
    "pv", StringMeta("Full pv of demand and default for rbv"), "",
    "rbv", StringMeta("Override for rbv"), "",
    "rbvSuff", StringMeta("Set rbv to pv + rbv_suff"), "",
    "widget", ChoiceMeta("Widget type", [""] + widget_types), "",
    "inport", ChoiceMeta("Inport type", [""] + port_types), "",
    "group", StringMeta("If given, which GUI group should we attach to"), "",
    "config", BooleanMeta("Should this field be loaded/saved?"), True,
    "minDelta", NumberMeta(
        "float64", "Minimum time between attribute updates in seconds"), 0.05,
    "timeout", NumberMeta(
        "float64", "Max time to wait for puts to complete, <0 is forever"), 5.0)
class CAPart(AttributePart):
    """Abstract class for exposing PVs as `Attribute` instances"""
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
        self.catools = CaToolsHelper.instance()
        self._update_after = 0
        super(CAPart, self).__init__(params)

    def is_writeable(self):
        return bool(self.params.pv)

    def get_writeable_func(self):
        return self.caput

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
        ca_values = self.catools.caget(
            pvs, format=self.catools.FORMAT_CTRL, datatype=self.get_datatype())
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]
        self.set_initial_metadata(ca_values[0])
        self.update_value(ca_values[0])
        # now setup monitor on rbv
        self.monitor = self.catools.camonitor(
            self.params.rbv, self.monitor_callback,
            format=self.catools.FORMAT_TIME, datatype=self.get_datatype(),
            notify_disconnect=True)

    @StatefulController.Disable
    def close_monitor(self, context=None):
        if self.monitor is not None:
            self.monitor.close()
            self.monitor = None

    def format_caput_value(self, value):
        self.log.info("caput -c -w %s %s %s",
                      self.params.timeout, self.params.pv, value)
        return value

    def caput(self, value):
        value = self.format_caput_value(value)
        if self.params.timeout < 0:
            timeout = None
        else:
            timeout = self.params.timeout
        self.catools.caput(
            self.params.pv, value, wait=True, timeout=timeout,
            datatype=self.get_datatype())
        # now do a caget
        value = self.catools.caget(
            self.params.rbv,
            format=self.catools.FORMAT_TIME, datatype=self.get_datatype())
        self.update_value(value)

    def monitor_callback(self, value):
        now = time.time()
        delta = now - self._update_after
        self.update_value(value)
        # See how long to sleep for to make sure we don't get more than one
        # update at < minDelta interval
        if delta > self.params.minDelta:
            # If we were more than minDelta late then reset next update time
            self._update_after = now + self.params.minDelta
        elif delta < 0:
            # If delta is less than zero sleep for a bit
            self.catools.cothread.Sleep(-delta)
        else:
            # If we were within the delta window just increment next update
            self._update_after += self.params.minDelta

    def update_value(self, value):
        if not value.ok:
            self.attr.set_value(None, alarm=Alarm.invalid("PV disconnected"))
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
            value = self.attr.meta.validate(value)
            self.attr.set_value_alarm_ts(value, alarm, ts)
