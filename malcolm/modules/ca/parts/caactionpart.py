from cothread import catools

from malcolm.controllers.builtin import StatefulController
from malcolm.core import Part, method_takes, REQUIRED, MethodModel
from malcolm.modules.builtin.vmetas import StringMeta, NumberMeta, BooleanMeta


@method_takes(
    "name", StringMeta("name of the created method"), REQUIRED,
    "description", StringMeta("desc of created method"), REQUIRED,
    "pv", StringMeta("full pv to write to when method called"), REQUIRED,
    "statusPv", StringMeta("Status pv to see if successful"), None,
    "goodStatus", StringMeta("Good value for status pv"), "",
    "value", NumberMeta("int32", "value to write to pv when method called"), 1,
    "wait", BooleanMeta("Wait for caput callback?"), True)
class CAActionPart(Part):
    def __init__(self, params):
        self.method = None
        self.params = params
        super(CAActionPart, self).__init__(params.name)

    def create_methods(self):
        # Method instance
        self.method = MethodModel(self.params.description)
        # TODO: set widget tag?
        yield self.params.name, self.method, self.caput

    @StatefulController.Reset
    def connect_pvs(self, _):
        pvs = [self.params.pv]
        if self.params.statusPv:
            pvs.append(self.params.statusPv)
        ca_values = catools.caget(pvs)
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]

    def caput(self):
        if self.params.wait:
            cmd = "caput -c -w 1000"
        else:
            cmd = "caput"
        self.log_debug("%s %s %s", cmd, self.params.pv, self.params.value)
        catools.caput(
            self.params.pv, self.params.value,
            wait=self.params.wait, timeout=None)
        if self.params.statusPv:
            value = catools.caget(
                self.params.statusPv,
                datatype=catools.DBR_STRING)
            assert value == self.params.goodStatus, \
                "Action '%s %s %s' failed with status %r" % (
                    cmd, self.params.pv, self.params.value, value)
