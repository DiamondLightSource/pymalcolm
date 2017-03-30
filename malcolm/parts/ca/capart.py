from malcolm.core import method_takes, REQUIRED
from malcolm.parts.builtin.attributepart import AttributePart
from malcolm.core.vmetas import StringMeta, ChoiceMeta, BooleanMeta
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.parts.ca.cothreadimporter import CothreadImporter
from malcolm.tags import widget_types, inport, port_types


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
    # Camonitor subscription
    monitor = None

    def __init__(self, process, params):
        self.cothread, self.catools = CothreadImporter.get_cothread(process)
        # Format for all caputs
        self.ca_format = self.catools.FORMAT_TIME
        super(CAPart, self).__init__(process, params)

    def store_params(self, params):
        if not params.rbv and not params.pv:
            raise ValueError('Must pass pv or rbv')
        if not params.rbv:
            if params.rbvSuff:
                params.rbv = params.pv + params.rbvSuff
            else:
                params.rbv = params.pv
        super(CAPart, self).store_params(params)

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

    @DefaultController.Reset
    def reset(self, task=None):
        # release old monitor
        self.close_monitor()
        # make the connection in cothread's thread, use caget for initial value
        pvs = [self.params.rbv]
        if self.params.pv:
            pvs.append(self.params.pv)
        ca_values = self.cothread.CallbackResult(
            self.catools.caget, pvs,
            format=self.catools.FORMAT_CTRL, datatype=self.get_datatype())
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]
        self.set_initial_metadata(ca_values[0])
        self.update_value(ca_values[0])
        self.log_debug("ca values connected %s", ca_values)
        # now setup monitor on rbv
        self.monitor = self.cothread.CallbackResult(
            self.catools.camonitor, self.params.rbv, self.update_value,
            format=self.catools.FORMAT_TIME, datatype=self.get_datatype(),
            notify_disconnect=True, all_updates=True)

    @DefaultController.Disable
    def close_monitor(self, task=None):
        if self.monitor is not None:
            self.cothread.CallbackResult(self.monitor.close)
            self.monitor = None

    def format_caput_value(self, value):
        self.log_info("caput -c -w 1000 %s %s", self.params.pv, value)
        return value

    def caput(self, value):
        value = self.format_caput_value(value)
        self.cothread.CallbackResult(
            self.catools.caput, self.params.pv, value, wait=True, timeout=None,
            datatype=self.get_datatype())
        # now do a caget
        value = self.cothread.CallbackResult(
            self.catools.caget, self.params.rbv,
            format=self.catools.FORMAT_TIME, datatype=self.get_datatype())
        self.update_value(value)

    def update_value(self, value):
        # TODO: make Alarm from value.status and value.severity
        # TODO: make Timestamp from value.timestamp
        if not value.ok:
            # TODO: set disconnect
            self.attr.set_value(None)
        else:
            # update value
            self.attr.set_value(value)
