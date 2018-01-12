from annotypes import Anno

from malcolm.modules.builtin.controllers import InitHook, ResetHook
from malcolm.core import Part, PartRegistrar
from ..util import CaToolsHelper, Name, Description, Pv


with Anno("Status pv to see if successful"):
    StatusPv = str
with Anno("Good value for status pv"):
    GoodStatus = str
with Anno("PV containing error message if unsuccessful"):
    MessagePv = str
with Anno("Value to write to pv when method called"):
    Value = int
with Anno("Wait for caput callback?"):
    Wait = bool


class CAActionPart(Part):
    """Group a number of PVs together that represent a method like acquire()"""
    def __init__(self,
                 name,  # type: Name
                 description,  # type: Description
                 pv="",  # type: Pv
                 statusPv="",  # type: StatusPv
                 goodStatus="",  # type: GoodStatus
                 messagePv="",  # type: MessagePv
                 value=1,  # type: Value
                 wait=True,  # type: Wait
                 ):
        # type: (...) -> None
        super(CAActionPart, self).__init__(name)
        self.method = None
        self.catools = CaToolsHelper.instance()
        self.description = description
        self.pv = pv
        self.statusPv = statusPv
        self.goodStatus = goodStatus
        self.messagePv = messagePv
        self.value = value
        self.wait = wait

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.method = registrar.add_method_model(
            self.caput, self.name, self.description)
        registrar.attach_to_hook(self.connect_pvs, InitHook, ResetHook)

    def connect_pvs(self, _):
        pvs = [self.pv]
        if self.statusPv:
            pvs.append(self.statusPv)
        if self.messagePv:
            pvs.append(self.messagePv)
        ca_values = self.catools.caget(pvs)
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]

    def caput(self):
        self.log.info("caput %s %s", self.pv, self.value)
        self.catools.caput(
            self.pv, self.value,
            wait=self.wait, timeout=None)
        if self.statusPv:
            status = self.catools.caget(
                self.statusPv,
                datatype=self.catools.DBR_STRING)
            if self.messagePv:
                message = " %s:" % self.catools.caget(
                    self.messagePv,
                    datatype=self.catools.DBR_CHAR_STR)
            else:
                message = ""
            assert status == self.goodStatus, \
                "Status %s:%s while performing 'caput %s %s'" % (
                    status, message, self.pv, self.value)
