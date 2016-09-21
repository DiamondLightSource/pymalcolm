import cothread
from cothread import catools

from malcolm.core import Part, method_takes, REQUIRED, MethodMeta
from malcolm.core.vmetas import StringMeta, NumberMeta, BooleanMeta
from malcolm.controllers.defaultcontroller import DefaultController


@method_takes(
    "name", StringMeta("name of the created method"), REQUIRED,
    "description", StringMeta("desc of created method"), REQUIRED,
    "pv", StringMeta("full pv to write to when method called"), REQUIRED,
    "status_pv", StringMeta("Status pv to see if successful"), None,
    "good_status", StringMeta("Good value for status pv"), "",
    "value", NumberMeta("int32", "value to write to pv when method called"), 1,
    "wait", BooleanMeta("Wait for caput callback?"), True)
class CAActionPart(Part):
    method = None

    def create_methods(self):
        # MethodMeta instance
        self.method = MethodMeta(self.params.description)
        yield self.params.name, self.method, self.caput

    @DefaultController.Resetting
    def connect_pvs(self, _):
        # make the connection in cothread's thread
        pvs = [self.params.pv]
        if self.params.status_pv:
            pvs.append(self.params.status_pv)
        ca_values = cothread.CallbackResult(catools.caget, pvs)
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]

    def caput(self):
        if self.params.wait:
            cmd = "caput -c -w 1000"
        else:
            cmd = "caput"
        self.log_info("%s %s %s", cmd, self.params.pv, self.params.value)
        cothread.CallbackResult(
            catools.caput, self.params.pv, self.params.value,
            wait=self.params.wait, timeout=None)
        if self.params.status_pv:
            value = cothread.CallbackResult(
                catools.caget, self.params.status_pv,
                datatype=catools.DBR_STRING)
            assert value == self.params.good_status, \
                "Action failed with status %r" % (value,)
