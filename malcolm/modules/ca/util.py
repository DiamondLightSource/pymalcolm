import threading
import time

from annotypes import Anno, TYPE_CHECKING, add_call_types

from malcolm.core import Queue, VMeta, Alarm, AlarmStatus, TimeStamp, \
    Loggable, Registrar
from malcolm.compat import maybe_import_cothread
from malcolm.modules.builtin.util import set_tags, Name, Description, AWidget, \
    Group, Config, InPort
from malcolm.modules.builtin.controllers import InitHook, ResetHook, DisableHook

if TYPE_CHECKING:
    from typing import Callable, Any


with Anno("Full pv of demand and default for rbv"):
    Pv = str
with Anno("Override for rbv"):
    Rbv = str
with Anno("Set rbv to pv + rbv_suff"):
    RbvSuff = str
with Anno("Minimum time between attribute updates in seconds"):
    MinDelta = float
with Anno("Max time to wait for puts to complete, <0 is forever"):
    Timeout = float


class CAAttribute(Loggable):
    def __init__(self,
                 meta,  # type: VMeta
                 datatype,  # type: Any
                 pv="",  # type: Pv
                 rbv="",  # type: Rbv
                 rbvSuff="",  # type: RbvSuff
                 minDelta=0.05,  # type: MinDelta
                 timeout=5.0,  # type: Timeout
                 inport=None,  # type: InPort
                 widget=None,  # type: AWidget
                 group=None,  # type: Group
                 config=True,  # type: Config
                 on_connect=None,  # type: Callable
                 ):
        # type: (...) -> None
        writeable = bool(pv)
        set_tags(meta, writeable, config, group, widget, inport)
        if not rbv and not pv:
            raise ValueError('Must pass pv or rbv')
        if not rbv:
            if rbvSuff:
                rbv = pv + rbvSuff
            else:
                rbv = pv
        self.pv = pv
        self.rbv = rbv
        self.datatype = datatype
        self.minDelta = minDelta
        self.timeout = timeout
        self.on_connect = on_connect
        self.attr = meta.create_attribute_model()
        # Camonitor subscription
        self.monitor = None
        self.catools = CaToolsHelper.instance()
        self._update_after = 0
        super(CAAttribute, self).__init__(pv=pv, rbv=rbv)

    @add_call_types
    def reconnect(self):
        # release old monitor
        self.disconnect()
        # make the connection in cothread's thread, use caget for initial value
        pvs = [self.rbv]
        if self.pv:
            pvs.append(self.pv)
        ca_values = self.catools.caget(
            pvs, format=self.catools.FORMAT_CTRL, datatype=self.datatype)
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]
        if self.on_connect:
            self.on_connect(ca_values[0])
        self._update_value(ca_values[0])
        # now setup monitor on rbv
        self.monitor = self.catools.camonitor(
            self.rbv, self._monitor_callback,
            format=self.catools.FORMAT_TIME, datatype=self.datatype,
            notify_disconnect=True)

    @add_call_types
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
        self.catools.caput(
            self.pv, value, wait=True, timeout=timeout,
            datatype=self.datatype)
        # now do a caget
        value = self.catools.caget(
            self.rbv,
            format=self.catools.FORMAT_TIME, datatype=self.datatype)
        self._update_value(value)

    def _monitor_callback(self, value):
        now = time.time()
        delta = now - self._update_after
        self._update_value(value)
        # See how long to sleep for to make sure we don't get more than one
        # update at < minDelta interval
        if delta > self.minDelta:
            # If we were more than minDelta late then reset next update time
            self._update_after = now + self.minDelta
        elif delta < 0:
            # If delta is less than zero sleep for a bit
            self.catools.cothread.Sleep(-delta)
        else:
            # If we were within the delta window just increment next update
            self._update_after += self.minDelta

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

    def attach_hooks(self, registrar):
        # type: (Registrar) -> None
        registrar.attach_to_hook(self.disconnect, DisableHook)
        registrar.attach_to_hook(self.reconnect, InitHook, ResetHook)


def _import_cothread(q):
    import cothread
    from cothread import catools
    from cothread.input_hook import _install_readline_hook
    _install_readline_hook(None)
    q.put((cothread, catools))
    # Wait forever
    cothread.Event().Wait()


class CaToolsHelper(object):
    _instance = None

    def __init__(self):
        assert not self._instance, \
            "Can't create more than one instance of Singleton. Use instance()"
        self.cothread = maybe_import_cothread()
        if self.cothread:
            # We can use it in this thread
            from cothread import catools
            self.in_cothread_thread = True
        else:
            # We need our own thread to run it in
            q = Queue()
            threading.Thread(target=_import_cothread, args=(q,)).start()
            self.cothread, catools = q.get()
            self.in_cothread_thread = False
        self.catools = catools
        self.DBR_STRING = catools.DBR_STRING
        self.DBR_LONG = catools.DBR_LONG
        self.DBR_DOUBLE = catools.DBR_DOUBLE
        self.FORMAT_CTRL = catools.FORMAT_CTRL
        self.FORMAT_TIME = catools.FORMAT_TIME
        self.DBR_ENUM = catools.DBR_ENUM
        self.DBR_CHAR_STR = catools.DBR_CHAR_STR

    def caget(self, *args, **kwargs):
        if self.in_cothread_thread:
            return self.catools.caget(*args, **kwargs)
        else:
            return self.cothread.CallbackResult(
                self.catools.caget, *args, **kwargs)

    def caput(self, *args, **kwargs):
        if self.in_cothread_thread:
            return self.catools.caput(*args, **kwargs)
        else:
            return self.cothread.CallbackResult(
                self.catools.caput, *args, **kwargs)

    def camonitor(self, *args, **kwargs):
        if self.in_cothread_thread:
            return self.catools.camonitor(*args, **kwargs)
        else:
            return self.cothread.CallbackResult(
                self.catools.camonitor, *args, **kwargs)

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = CaToolsHelper()
        return cls._instance

