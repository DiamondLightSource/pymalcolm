import cothread
from cothread import catools

from malcolm.core import Part, Attribute, method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta
from malcolm.controllers.defaultcontroller import DefaultController


def capart_takes(*args):
    args = (
        "name", StringMeta("name of the created attribute"), REQUIRED,
        "description", StringMeta("desc of created attribute"), REQUIRED,
        "pv", StringMeta("full pv of demand and default for rbv"), None,
        "rbv", StringMeta("override for rbv"), None,
        "rbv_suff", StringMeta("set rbv ro pv + rbv_suff"), None,
    ) + args
    return method_takes(*args)


class CAPart(Part):
    # Camonitor subscription
    monitor = None
    # Format for all caputs
    ca_format = catools.FORMAT_CTRL
    # Attribute instance
    attr = None

    def create_attributes(self):
        params = self.params
        if params.pv is None and params.rbv is None:
            raise ValueError('Must pass pv or rbv')
        if params.rbv is None:
            if params.rbv_suff is None:
                params.rbv = params.pv
            else:
                params.rbv = params.pv + params.rbv_suff
        # The attribute we will be publishing
        self.attr = self.create_meta(params.description).make_attribute()
        if self.params.pv:
            writeable_func = self.caput
        else:
            writeable_func = None
        yield params.name, self.attr, writeable_func

    def create_meta(self, description):
        raise NotImplementedError

    def get_datatype(self):
        raise NotImplementedError

    @DefaultController.Resetting
    def connect_pvs(self, _=None):
        # release old monitor
        self.close_monitor()
        # make the connection in cothread's thread, use caget for initial value
        pvs = [self.params.rbv]
        if self.params.pv:
            pvs.append(self.params.pv)
        ca_values = cothread.CallbackResult(
            catools.caget, pvs,
            format=self.ca_format, datatype=self.get_datatype())
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]
        self.update_value(ca_values[0])
        self.log_debug("ca values connected %s", ca_values)
        # now setup monitor on rbv
        self.monitor = cothread.CallbackResult(
            catools.camonitor, self.params.rbv, self.on_update,
            format=self.ca_format, datatype=self.get_datatype(),
            notify_disconnect=True)

    @DefaultController.Disabling
    def close_monitor(self, _=None):
        if self.monitor is not None:
            cothread.CallbackResult(self.monitor.close)
            self.monitor = None

    def caput(self, value):
        try:
            l = len(value)
        except TypeError:
            if isinstance(value, bool):
                value = int(value)
            self.log_info("caput -c -w 1000 %s %s", self.params.pv, value)
        else:
            v = " ".join(str(x) for x in value)
            self.log_info("caput -a -w 1000 %s %d %s", self.params.pv, l, v)
        cothread.CallbackResult(
            catools.caput, self.params.pv, value, wait=True, timeout=None,
            datatype=self.get_datatype())
        # now do a caget
        value = cothread.CallbackResult(
            catools.caget, self.params.rbv,
            format=self.ca_format, datatype=self.get_datatype())
        self.update_value(value)

    def on_update(self, value):
        # Called on cothread's queue, so don't block
        self.process.spawn(self.update_value, value)

    def update_value(self, value):
        self.log_debug("Camonitor update %r", value)
        # TODO: make Alarm from value.status and value.severity
        # TODO: make Timestamp from value.timestamp
        if not value.ok:
            # TODO: set disconnect
            self.attr.set_value(None)
        else:
            # update value
            self.attr.set_value(value)
