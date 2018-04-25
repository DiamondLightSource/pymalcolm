from annotypes import Anno

from malcolm.core import Part, PartRegistrar
from malcolm.modules import builtin
from ..util import CaToolsHelper, APartName, AMetaDescription, APv

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
                 name,  # type: APartName
                 description,  # type: AMetaDescription
                 pv="",  # type: APv
                 status_pv="",  # type: StatusPv
                 good_status="",  # type: GoodStatus
                 message_pv="",  # type: MessagePv
                 value=1,  # type: Value
                 wait=True,  # type: Wait
                 ):
        # type: (...) -> None
        super(CAActionPart, self).__init__(name)
        self.catools = CaToolsHelper.instance()
        self.description = description
        self.pv = pv
        self.status_pv = status_pv
        self.good_status = good_status
        self.message_pv = message_pv
        self.value = value
        self.wait = wait
        # Hooks
        self.register_hooked((builtin.hooks.InitHook,
                              builtin.hooks.ResetHook), self.connect_pvs)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(CAActionPart, self).setup(registrar)
        registrar.add_method_model(self.caput, self.name, self.description)

    def connect_pvs(self):
        pvs = [self.pv]
        if self.status_pv:
            pvs.append(self.status_pv)
        if self.message_pv:
            pvs.append(self.message_pv)
        ca_values = self.catools.caget(pvs)
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]

    def caput(self):
        self.log.info("caput %s %s", self.pv, self.value)
        self.catools.caput(
            self.pv, self.value,
            wait=self.wait, timeout=None)
        if self.status_pv:
            status = self.catools.caget(
                self.status_pv,
                datatype=self.catools.DBR_STRING)
            if self.message_pv:
                message = " %s:" % self.catools.caget(
                    self.message_pv,
                    datatype=self.catools.DBR_CHAR_STR)
            else:
                message = ""
            assert status == self.good_status, \
                "Status %s:%s while performing 'caput %s %s'" % (
                    status, message, self.pv, self.value)
