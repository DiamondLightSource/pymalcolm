import cothread
from cothread import catools

from malcolm.core.part import Part
from malcolm.core.controller import Controller
from malcolm.core.attribute import Attribute


class CAPart(Part):

    def create_attribute(self, meta, pv=None, rbv=None, rbv_suff=None,
                         ca_ctrl=False):
        if pv is None and rbv is None:
            raise ValueError('must pass pv rbv')
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
        # The attribute we will be publishing
        self.attr = Attribute(self.meta)
        self.attr.set_put_function(self.caput)
        self.block.add_attribute(self.attr)
        # camonitor subscription
        self.monitor = None
        self.ca_format = catools.FORMAT_TIME

    def set_ca_ctrl(self):
        self.ca_format = catools.FORMAT_CTRL

    def get_datatype(self):
        raise NotImplementedError

    @Controller.Resetting
    def connect_pvs(self):
        # release old monitor
        self.close_monitor()
        # make the connection in cothread's thread, use caget for initial value
        pvs = [self.rbv]
        if self.pv:
            pvs.append(self.pv)
        ca_value = cothread.CallbackResult(catools.caget, pvs
                                           , format=self.ca_format)
        # check connection is ok
        for i in range(0,len(pvs)):
            assert ca_value[i].ok, "CA connect failed with %s" % \
                                   ca_value.state_strings[ca_value[i].state]
        self.update_value(ca_value[0])
        # now setup monitor on rbv
        self.monitor = catools.camonitor(
            self.rbv, self.on_update, format=self.ca_format,
            datatype=self.get_datatype(), notify_disconnect=True)

    def close_monitor(self):
        if self.monitor is not None:
            cothread.CallbackResult(self.monitor.close)
            self.monitor = None

    def caput(self, value):
        cothread.CallbackResult(
            catools.caput, self.pv, value, wait=True, timeout=None,
            datatype=self.get_datatype())
        # now do a caget
        value = cothread.CallbackResult(
            catools.caget, self.rbv, datatype=self.get_datatype())
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
