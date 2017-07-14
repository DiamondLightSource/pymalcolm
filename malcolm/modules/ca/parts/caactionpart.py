from malcolm.modules.builtin.controllers import StatefulController
from malcolm.core import Part, method_takes, REQUIRED, MethodModel
from malcolm.modules.builtin.vmetas import StringMeta, NumberMeta, BooleanMeta
from .catoolshelper import CaToolsHelper


@method_takes(
    "name", StringMeta("Name of the created method"), REQUIRED,
    "description", StringMeta("desc of created method"), REQUIRED,
    "pv", StringMeta("full pv to write to when method called"), REQUIRED,
    "statusPv", StringMeta("Status pv to see if successful"), "",
    "goodStatus", StringMeta("Good value for status pv"), "",
    "messagePv", StringMeta("PV containing error message if unsuccessful"), "",
    "value", NumberMeta("int32", "value to write to pv when method called"), 1,
    "wait", BooleanMeta("Wait for caput callback?"), True)
class CAActionPart(Part):
    """Group a number of PVs together that represent a method like acquire()"""
    def __init__(self, params):
        """
        Args:
            params (Map): The params to initialize with
        """
        self.method = None
        self.params = params
        self.catools = CaToolsHelper.instance()
        super(CAActionPart, self).__init__(params.name)

    def create_method_models(self):
        # Method instance
        self.method = MethodModel(self.params.description)
        # TODO: set widget tag?
        yield self.params.name, self.method, self.caput

    @StatefulController.Reset
    def connect_pvs(self, _):
        pvs = [self.params.pv]
        if self.params.statusPv:
            pvs.append(self.params.statusPv)
        ca_values = self.catools.caget(pvs)
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]

    def caput(self):
        if self.params.wait:
            cmd = "caput -c -w 1000"
        else:
            cmd = "caput"
        self.log.info("%s %s %s", cmd, self.params.pv, self.params.value)
        self.catools.caput(
            self.params.pv, self.params.value,
            wait=self.params.wait, timeout=None)
        if self.params.statusPv:
            status = self.catools.caget(
                self.params.statusPv,
                datatype=self.catools.DBR_STRING)
            if self.params.messagePv:
                message = " %s:" % self.catools.caget(
                    self.params.messagePv,
                    datatype=self.catools.DBR_CHAR_STR)
            else:
                message = ""
            assert status == self.params.goodStatus, \
                "Status %s:%s while performing '%s %s %s'" % (
                    status, message, cmd, self.params.pv, self.params.value)
