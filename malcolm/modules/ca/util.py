import time

from annotypes import Anno, TYPE_CHECKING
from cothread import catools

from malcolm.core import sleep, VMeta, Alarm, AlarmStatus, TimeStamp, \
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


class CAAttribute(Loggable):
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
        set_tags(meta, writeable, config, group, widget, sink_port)
        if not rbv and not pv:
            raise ValueError('Must pass pv or rbv')
        if not rbv:
            if rbv_suffix:
                rbv = pv + rbv_suffix
            else:
                rbv = pv
        self.pv = pv
        self.rbv = rbv
        self.datatype = datatype
        self.min_delta = min_delta
        self.timeout = timeout
        self.on_connect = on_connect
        self.attr = meta.create_attribute_model()
        # Camonitor subscription
        self.monitor = None
        self._update_after = 0

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

    def disconnect(self):
        if self.monitor is not None:
            self.monitor.close()
            self.monitor = None

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

    def _monitor_callback(self, value):
        now = time.time()
        delta = now - self._update_after
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

    def _update_value(self, value):
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

    def setup(self, registrar, name, register_hooked, writeable_func=None):
        # type: (PartRegistrar, str, Register, Callable[[Any], None]) -> None
        if self.pv:
            if writeable_func is None:
                writeable_func = self.caput
        else:
            writeable_func = None
        registrar.add_attribute_model(name, self.attr, writeable_func)
        register_hooked(DisableHook, self.disconnect)
        register_hooked((InitHook, ResetHook), self.reconnect)


def assert_connected(ca_values):
    # check connection is ok
    for i, v in enumerate(ca_values):
        assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]
    return ca_values
