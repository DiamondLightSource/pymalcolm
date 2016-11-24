from malcolm.core import Part, method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.parts.ca.cothreadimporter import CothreadImporter


@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Desc of created attribute"), REQUIRED,
    "pv", StringMeta("Full pv of demand and default for rbv"), "",
    "rbv", StringMeta("Override for rbv"), "",
    "rbvSuff", StringMeta("Set rbv ro pv + rbv_suff"), "",
    "widget", StringMeta("Widget, like 'combo' or 'textinput'"), "",
    "inportType", StringMeta(
        "Flowgraph port Type if it is one (like 'CS' or 'NDArray')"), "")
class CAPart(Part):
    # Camonitor subscription
    monitor = None
    # Attribute instance
    attr = None

    def __init__(self, process, params):
        self.cothread, self.catools = CothreadImporter.get_cothread(process)
        # Format for all caputs
        self.ca_format = self.catools.FORMAT_CTRL
        super(CAPart, self).__init__(process, params)

    def create_attributes(self):
        params = self.params
        if not params.rbv and not params.pv:
            raise ValueError('Must pass pv or rbv')
        if not params.rbv:
            if params.rbvSuff:
                params.rbv = params.pv + params.rbvSuff
            else:
                params.rbv = params.pv
        # Find the tags
        tags = self.create_tags(params)
        # The attribute we will be publishing
        self.attr = self.create_meta(params.description, tags).make_attribute()
        if self.params.pv:
            writeable_func = self.caput
        else:
            writeable_func = None
        yield params.name, self.attr, writeable_func

    def create_tags(self, params):
        tags = []
        if params.widget:
            assert ":" not in params.widget, \
                "Widget tag %r should not specify 'widget:' prefix" \
                % params.widget
            tags.append("widget:%s" % params.widget)
        if params.inportType:
            assert ":" not in params.inportType, \
                "Inport tag %r should not specify 'flowgraph:inport:' prefix" \
                % params.inportType
            tags.append("flowgraph:inport:%s:" % params.inportType)
        return tags

    def create_meta(self, description, tags):
        raise NotImplementedError

    def get_datatype(self):
        raise NotImplementedError

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
            format=self.ca_format, datatype=self.get_datatype())
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]
        self.update_value(ca_values[0])
        self.log_debug("ca values connected %s", ca_values)
        # now setup monitor on rbv
        self.monitor = self.cothread.CallbackResult(
            self.catools.camonitor, self.params.rbv, self.update_value,
            format=self.ca_format, datatype=self.get_datatype(),
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
            format=self.ca_format, datatype=self.get_datatype())
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
