import time

from annotypes import Anno, Array, TYPE_CHECKING

from malcolm.core import sleep, VMeta, Alarm, AlarmStatus, TimeStamp, \
    Loggable, APartName, AMetaDescription, Hook, PartRegistrar, DEFAULT_TIMEOUT
from malcolm.modules import builtin

if TYPE_CHECKING:
    from typing import Callable, Any, Union, Type, Sequence, Optional, List

    Hooks = Union[Type[Hook], Sequence[Type[Hook]]]
    ArgsGen = Callable[(), List[str]]
    Register = Callable[(Hooks, Callable, Optional[ArgsGen]), None]

# Store them here for re-export
APartName = APartName
AMetaDescription = AMetaDescription
AWidget = builtin.util.AWidget
AGroup = builtin.util.AGroup
AConfig = builtin.util.AConfig
ASinkPort = builtin.util.ASinkPort


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
with Anno("List of PVs to monitor"):
    APvList = Array[str]
with Anno("List of names to give to monitored PVs"):
    ANameList = Array[str]
with Anno("Set rbv to pv + rbv_suffix"):
    ARbvSuffix = str
with Anno("Minimum time between attribute updates in seconds"):
    AMinDelta = float
with Anno("Max time to wait for puts to complete, <0 is forever"):
    ATimeout = float
with Anno("Get limits from PV (HOPR & LOPR)"):
    AGetLimits = bool


class CABase(Loggable):
    def __init__(self,
                 meta,  # type: VMeta
                 datatype,  # type: Any
                 writeable,  # type: bool
                 min_delta=0.05,  # type: AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: ATimeout
                 sink_port=None,  # type: ASinkPort
                 widget=None,  # type: AWidget
                 group=None,  # type: AGroup
                 config=1,  # type: AConfig
                 on_connect=None,  # type: Callable[[Any], None]
                 ):
        # type: (...) -> None
        self.writeable = writeable
        builtin.util.set_tags(
            meta, writeable, config, group, widget, sink_port)
        self.datatype = datatype
        self.min_delta = min_delta
        self.timeout = timeout
        self.on_connect = on_connect
        self.attr = meta.create_attribute_model()
        # Camonitor subscription
        self.monitor = None
        self._update_after = 0
        self._local_value = None

    def disconnect(self):
        if self.monitor is not None:
            if hasattr(self.monitor, "__len__"):
                for monitor in self.monitor:
                    monitor.close()
            else:
                self.monitor.close()
            self.monitor = None

    def _update_value(self, value):
        # Attribute value might not be raw PV, PV which triggered update is
        # passed as status
        if not value.ok:
            self.attr.set_value(
                self.attr.value, alarm=Alarm.disconnected("PV disconnected"))
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

    def reconnect(self):
        pass

    def caput(self, value):
        pass

    def setup(self, registrar, name, register_hooked, writeable_func=None):
        # type: (PartRegistrar, str, Register, Callable[[Any], None]) -> None
        if self.writeable:
            if writeable_func is None:
                writeable_func = self.caput
        else:
            writeable_func = None
        registrar.add_attribute_model(name, self.attr, writeable_func)
        register_hooked(builtin.hooks.DisableHook, self.disconnect)
        register_hooked((builtin.hooks.InitHook, builtin.hooks.ResetHook),
                        self.reconnect)

    def _monitor_callback(self, value, value_index=None):
        now = time.time()
        delta = now - self._update_after
        if value_index is not None and hasattr(self, "name_list"):
            value_key = self.name_list[value_index]
            self._local_value[value_key] = value
            self._local_value.raw_stamp = getattr(value, "raw_stamp", (None, None))
            self._local_value.ok = (self._local_value.ok or value.ok)
            self._local_value.severity = max(self._local_value.severity, value.severity)
            self._update_value(self._local_value)
        else:
            self._update_value(value)
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


class CAAttribute(CABase):
    def __init__(self,
                 meta,  # type: VMeta
                 datatype,  # type: Any
                 pv="",  # type: APv
                 rbv="",  # type: ARbv
                 rbv_suffix="",  # type: ARbvSuffix
                 min_delta=0.05,  # type: AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: ATimeout
                 sink_port=None,  # type: ASinkPort
                 widget=None,  # type: AWidget
                 group=None,  # type: AGroup
                 config=1,  # type: AConfig
                 on_connect=None,  # type: Callable[[Any], None]
                 ):
        # type: (...) -> None
        self.set_logger(pv=pv, rbv=rbv)
        writeable = bool(pv)
        super(CAAttribute, self).__init__(meta, datatype, writeable, min_delta, timeout, sink_port, widget, group,
                                          config, on_connect)
        if not rbv and not pv:
            raise ValueError('Must pass pv or rbv')
        if not rbv:
            if rbv_suffix:
                rbv = pv + rbv_suffix
            else:
                rbv = pv
        self.pv = pv
        self.rbv = rbv
        # Camonitor subscription
        self.monitor = None

    def reconnect(self):
        # release old monitor
        self.disconnect()
        # make the connection in cothread's thread, use caget for initial value
        pvs = [self.rbv]
        if self.pv and self.pv != self.rbv:
            pvs.append(self.pv)
        ca_values = assert_connected(catools.caget(
            pvs, format=catools.FORMAT_CTRL, datatype=self.datatype))

        if self.on_connect:
            self.on_connect(ca_values[0])
        self._update_value(ca_values[0])
        # now setup monitor on rbv
        self.monitor = catools.camonitor(
            self.rbv, self._monitor_callback,
            format=catools.FORMAT_TIME, datatype=self.datatype,
            notify_disconnect=True)

    def caput(self, value):
        if self.timeout < 0:
            timeout = None
        else:
            timeout = self.timeout
        self.log.info("caput %s %s", self.pv, value)
        catools.caput(
            self.pv, value, wait=True, timeout=timeout, datatype=self.datatype)
        # now do a caget
        value = catools.caget(
            self.rbv, format=catools.FORMAT_TIME, datatype=self.datatype)
        self._update_value(value)


class CATable(dict):
    ok = True
    severity = 0
    raw_stamp = (None, None)


class WaveformTableAttribute(CABase):
    def __init__(self,
                 meta,  # type: VMeta
                 datatype,  # type: Any
                 pv_list=(),  # type: APvList
                 name_list=(),  # type: ANameList
                 min_delta=0.05,  # type: AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: ATimeout
                 widget=None,  # type: AWidget
                 group=None,  # type: AGroup
                 config=1,  # type: AConfig
                 limits_from_pv=False,  # type: AGetLimits
                 on_connect=None  # type: Callable[[Any], None]
                 ):
        # type: (...) -> None
        logs = {}
        for ind, pv in enumerate(pv_list):
            logs[name_list[ind]] = pv

        self.set_logger(**logs)
        writeable = False
        super(WaveformTableAttribute, self).__init__(meta, datatype, writeable, min_delta, timeout, None, widget,
                                                     group, config, on_connect)
        if len(pv_list) == 0:
            raise ValueError('Must pass at least one PV')
        self.pv_list = pv_list
        self.name_list = name_list
        # Camonitor subscriptions
        self.monitor = None
        self._local_value = CATable()
        for name in name_list:
            self._local_value[name] = []
        self._update_after = 0
        self.limits_from_pv = limits_from_pv

    def reconnect(self):
        # release old monitor
        self.disconnect()
        # make the connection in cothread's thread, use caget for initial
        ca_values = assert_connected(catools.caget(
            self.pv_list, format=catools.FORMAT_CTRL, datatype=self.datatype))

        for ind, value in enumerate(ca_values):
            if self.on_connect:
                self.on_connect(value)
            self._local_value[self.name_list[ind]] = value
            self._local_value.severity = max(self._local_value.severity, value.severity)
            self._local_value.ok = self._local_value.ok or value.ok
        self._update_value(self._local_value)
        # now setup monitors for all the things
        self.monitor = catools.camonitor(self.pv_list, self._monitor_callback, format=catools.FORMAT_TIME,
                                         datatype=self.datatype, notify_disconnect=True)


def assert_connected(ca_values):
    # check connection is ok
    for i, v in enumerate(ca_values):
        assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]
    return ca_values
