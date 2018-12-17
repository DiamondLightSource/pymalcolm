import time

from annotypes import Anno, TYPE_CHECKING

from malcolm.core import sleep, Widget, VMeta, Alarm, AlarmStatus, TimeStamp, \
    Loggable, APartName, AMetaDescription, Hook, PartRegistrar, DEFAULT_TIMEOUT
from malcolm.modules.builtin.util import set_tags, AWidget, AGroup, AConfig, \
    ASinkPort
from malcolm.modules.builtin.hooks import InitHook, ResetHook, DisableHook

if TYPE_CHECKING:
    from typing import Callable, Any, Union, Type, Sequence, Optional, List

    Hooks = Union[Type[Hook], Sequence[Type[Hook]]]
    ArgsGen = Callable[(), List[str]]
    Register = Callable[(Hooks, Callable, Optional[ArgsGen]), None]


# Store them here for re-export
APartName = APartName
AMetaDescription = AMetaDescription


class CatoolsDeferred(object):
    """Deferred gets of catools things"""
    def __getattr__(self, item):
        from cothread import catools
        return getattr(catools, item)


catools = CatoolsDeferred()


with Anno("Full pv of demand and default for rbv"):
    APv = str
with Anno("Override for rbv"):
    ARbv = str
with Anno("Set rbv to pv + rbv_suffix"):
    ARbvSuffix = str
with Anno("Minimum time between attribute updates in seconds"):
    AMinDelta = float
with Anno("Max time to wait for puts to complete, <0 is forever"):
    ATimeout = float
with Anno("Get limits from PV (HOPR & LOPR)"):
    AGetLimits = bool


class Waveform2DAttribute(Loggable):
    def __init__(self,
                 meta,  # type: VMeta
                 datatype,  # type: Any
                 yData="",  # type: APv
                 xData="",  # type: ARbv
                 min_delta=0.05,  # type: AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: ATimeout
                 sink_port=None,  # type: ASinkPort
                 widget=None,  # type: AWidget
                 group=None,  # type: AGroup
                 config=1,  # type: AConfig
                 limits_from_pv=False,  # type: AGetLimits
                 on_connect=None  # type: Callable[[Any], None]
                 ):
        # type: (...) -> None
        self.set_logger(xData=xData, yData=yData)
        writeable = False
        set_tags(meta, writeable, config, group, widget, sink_port)
        self.xPv = xData
        self.yPv = yData
        self.datatype = datatype
        self.min_delta = min_delta
        self.timeout = timeout
        self.on_connect = on_connect
        self.attr = meta.create_attribute_model()
        # Camonitor subscriptions
        self.monitor = {"xData": None, "yData": None, "xLow": None, "yLow": None, "xHigh": None, "yHigh": None}
        self._update_after = 0
        self._local_value = {"xData": [], "yData": [], "xLow": None, "yLow": None, "xHigh": None, "yHigh": None}
        self.limits_from_pv = limits_from_pv

    def reconnect(self):
        # release old monitor
        self.disconnect()
        # make the connection in cothread's thread, use caget for initial value
        pvs = [self.yPv]
        if self.xPv:
            pvs.append(self.xPv)
        ca_values = assert_connected(catools.caget(
            pvs, format=catools.FORMAT_CTRL, datatype=self.datatype))

        if self.on_connect:
            self.on_connect(ca_values[0])
        self._update_value(ca_values[0])
        # now setup monitors for all the things
        self.monitor["yData"] = catools.camonitor(
            self.yPv, self._monitor_callback_yData,
            format=catools.FORMAT_TIME, datatype=self.datatype,
            notify_disconnect=True)
        if self.xPv:
            self.monitor["xData"] = catools.camonitor(
                self.xPv, self._monitor_callback_xData,
                format=catools.FORMAT_TIME, datatype=self.datatype,
                notify_disconnect=True)
        if self.limits_from_pv:
            self.monitor["yLow"] = catools.camonitor(
                self.yPv + ".LOPR", self._monitor_callback_yLow,
                format=catools.FORMAT_TIME, datatype=self.datatype,
                notify_disconnect=True)
            self.monitor["yHigh"] = catools.camonitor(
                self.yPv + ".HOPR", self._monitor_callback_yHigh,
                format=catools.FORMAT_TIME, datatype=self.datatype,
                notify_disconnect=True)
            if self.xPv:
                self.monitor["xLow"] = catools.camonitor(
                    self.xPv + ".LOPR", self._monitor_callback_xLow,
                    format=catools.FORMAT_TIME, datatype=self.datatype,
                    notify_disconnect=True)
                self.monitor["xHigh"] = catools.camonitor(
                    self.xPv + ".HOPR", self._monitor_callback_xHigh,
                    format=catools.FORMAT_TIME, datatype=self.datatype,
                    notify_disconnect=True)

    def disconnect(self):
        for monitor in self.monitor.keys():
            if self.monitor[monitor] is not None:
                self.monitor[monitor].close()
                self.monitor[monitor] = None

    def _monitor_callback_base(self, new_value, value_key):
        now = time.time()
        delta = now - self._update_after
        self._local_value[value_key] = new_value
        self._update_value(new_value)
        # See how long to sleep for to make sure we don't get more than one
        # update at < min_delta interval
        if delta > self.min_delta:
            # If we were more than min_delta late then reset next update time
            self._update_after = now + self.min_delta
        elif delta < 0:
            # If delta is less than zero sleep for a bit
            sleep(-delta)
        else:
            # If we were within the delta window just increment next update
            self._update_after += self.min_delta

    def _monitor_callback_xData(self, value):
        self._monitor_callback_base(value, "xData")

    def _monitor_callback_yData(self, value):
        self._monitor_callback_base(value, "yData")

    def _monitor_callback_xLow(self, value):
        self._monitor_callback_base(value, "xLow")

    def _monitor_callback_xHigh(self, value):
        self._monitor_callback_base(value, "xHigh")

    def _monitor_callback_yLow(self, value):
        self._monitor_callback_base(value, "yLow")

    def _monitor_callback_yHigh(self, value):
        self._monitor_callback_base(value, "yHigh")

    def _update_value(self, new_value):
        if not new_value.ok:
            self.attr.set_value(None, alarm=Alarm.invalid("PV disconnected"))
        else:
            if new_value.severity:
                alarm = Alarm(severity=new_value.severity,
                              status=AlarmStatus.RECORD_STATUS,
                              message="PV in alarm state")
            else:
                alarm = Alarm.ok
            # We only have a raw_stamp attr on monitor, the initial
            # caget with CTRL doesn't give us a timestamp
            ts = TimeStamp(*getattr(new_value, "raw_stamp", (None, None)))
            # new_value = self.attr.meta.validate(new_value)
            self.attr.set_value_alarm_ts(self._local_value, alarm, ts)

    def setup(self, registrar, name, register_hooked, writeable_func=None):
        # type: (PartRegistrar, str, Register, Callable[[Any], None]) -> None
        registrar.add_attribute_model(name, self.attr, writeable_func)
        register_hooked(DisableHook, self.disconnect)
        register_hooked((InitHook, ResetHook), self.reconnect)


def assert_connected(ca_values):
    # check connection is ok
    for i, v in enumerate(ca_values):
        assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]
    return ca_values
