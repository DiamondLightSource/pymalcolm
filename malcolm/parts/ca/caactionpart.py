import cothread
from cothread import catools

from malcolm.core import Part, method_takes, REQUIRED, MethodMeta
from malcolm.core.vmetas import StringMeta, NumberMeta, BooleanMeta
from malcolm.controllers.builtin import DefaultController


@method_takes(
    "name", StringMeta("name of the created method"), REQUIRED,
    "description", StringMeta("desc of created method"), REQUIRED,
    "pv", StringMeta("full pv to write to when method called"), REQUIRED,
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
        v = cothread.CallbackResult(catools.caget, self.params.pv)
        # check connection is ok
        assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]

    def caput(self):
        cothread.CallbackResult(
            catools.caput, self.params.pv, self.params.value,
            wait=self.params.wait, timeout=None)
