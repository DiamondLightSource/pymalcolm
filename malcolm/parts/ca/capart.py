import cothread
from cothread import catools

from malcolm.core.part import Part
from malcolm.core.controller import Controller
from malcolm.core.attribute import Attribute


class CAPart(Part):

    def create_attribute(self, meta, pv, rbv=None, rbv_suff=None,
                         long_string=False):
        if rbv is None:
            if rbv_suff is None:
                rbv = pv
            else:
                rbv = pv + rbv_suff
        # Meta instance
        self.meta = meta
        # Pv strings
        self.pv = pv
        self.rbv = rbv
        # should we put as a long string
        self.long_string = long_string
        # The attribute we will be publishing
        self.attr = Attribute(self.name, self.meta)
        self.attr.set_put_function(self.caput)
        self.block.add_attribute(self.attr)
        # camonitor subscription
        self.monitor = None

    def get_datatype(self):
        raise NotImplementedError

    @Controller.Resetting
    def connect_pvs(self):
        # release old monitor
        self.close_monitor()
        # need to make the connection in cothread's thread
        pvs = [self.pv, self.rbv]
        cainfo = cothread.CallbackResult(catools.connect, pvs, cainfo=True)
        # check connection is ok
        assert cainfo.ok, \
            "CA connect failed with %s" % cainfo.state_strings[cainfo.state]
        # now setup monitor on rbv
        self.monitor = catools.camonitor(
            self.rbv, on_update=self.on_update, format=catools.FORMAT_TIME,
            datatype=self.get_datatype(), notify_disconnect=True)

    def close_monitor(self):
        if self.monitor is not None:
            cothread.CallbackResult(self.monitor.close)
            self.monitor = None

    def caput(self, value):
        cothread.CallbackResult(
            catools.caput, self.pv, value, wait=True, timeout=None)
        # now do a caget
        value = cothread.CallbackResult(
            catools.caget, self.rbv)
        self.update_value(value)

    def on_update(self, value):
        # Called on cothread's queue, so don't block
        self.process.spawn(self.update_value, value)

    def update_value(self, value):
        self.log_debug("Camonitor update %r", value)
        # TODO: make Alarm from value.status and value.severity
        # TODO: make Timestamp from value.timestamp
        with self.block.lock:
            if not value.ok:
                # disconnect
                self.block.state.set_value(Controller.stateMachine.FAULT,
                                           notify=False)
                self.block.status.set_value("CA disconnect on %s" % value.name,
                                            notify=False)
                self.block.busy.set_value(False)
                self.close_monitor()
            else:
                # update value
                self.attr.set_value(value)
