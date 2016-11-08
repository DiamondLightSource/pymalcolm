from malcolm.core import Part, method_takes, REQUIRED, MethodMeta
from malcolm.core.vmetas import StringMeta, NumberMeta, BooleanMeta
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.parts.ca.cothreadimporter import CothreadImporter


@method_takes(
    "name", StringMeta("name of the created method"), REQUIRED,
    "description", StringMeta("desc of created method"), REQUIRED,
    "pv", StringMeta("full pv to write to when method called"), REQUIRED,
    "statusPv", StringMeta("Status pv to see if successful"), None,
    "goodStatus", StringMeta("Good value for status pv"), "",
    "value", NumberMeta("int32", "value to write to pv when method called"), 1,
    "wait", BooleanMeta("Wait for caput callback?"), True)
class CAActionPart(Part):
    method = None

    def __init__(self, process, params):
        self.cothread, self.catools = CothreadImporter.get_cothread(process)
        super(CAActionPart, self).__init__(process, params)

    def create_methods(self):
        # MethodMeta instance
        self.method = MethodMeta(self.params.description)
        # TODO: set widget tag?
        yield self.params.name, self.method, self.caput

    @DefaultController.Reset
    def connect_pvs(self, _):
        # make the connection in cothread's thread
        pvs = [self.params.pv]
        if self.params.statusPv:
            pvs.append(self.params.statusPv)
        ca_values = self.cothread.CallbackResult(self.catools.caget, pvs)
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]

    def caput(self):
        if self.params.wait:
            cmd = "caput -c -w 1000"
        else:
            cmd = "caput"
        self.log_info("%s %s %s", cmd, self.params.pv, self.params.value)
        self.cothread.CallbackResult(
            self.catools.caput, self.params.pv, self.params.value,
            wait=self.params.wait, timeout=None)
        if self.params.statusPv:
            value = self.cothread.CallbackResult(
                self.catools.caget, self.params.statusPv,
                datatype=self.catools.DBR_STRING)
            assert value == self.params.goodStatus, \
                "Action '%s %s %s' failed with status %r" % (
                    cmd, self.params.pv, self.params.value, value)
