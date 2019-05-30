import time

from annotypes import Anno

from malcolm.core import Part, PartRegistrar, Queue, TimeoutError
from malcolm.modules import builtin
from .. import util

with Anno("Status pv to see if successful"):
    AStatusPv = str
with Anno("Good value for status pv"):
    AGoodStatus = str
with Anno("PV containing error message if unsuccessful"):
    AMessagePv = str
with Anno("Value to write to pv when method called"):
    AValue = int
with Anno("Wait for caput callback?"):
    AWait = bool
with Anno("How long to wait for status_pv == good_status before returning"):
    AStatusTimeout = int


class CAActionPart(Part):
    """Group a number of PVs together that represent a method like acquire()
    """

    def __init__(self,
                 name,  # type: util.APartName
                 description,  # type: util.AMetaDescription
                 pv="",  # type: util.APv
                 status_pv="",  # type: AStatusPv
                 good_status="",  # type: AGoodStatus
                 status_timeout=1,  # type: AStatusTimeout
                 message_pv="",  # type: AMessagePv
                 value=1,  # type: AValue
                 wait=True,  # type: AWait
                 ):
        # type: (...) -> None
        super(CAActionPart, self).__init__(name)
        self.description = description
        self.pv = pv
        self.status_pv = status_pv
        self.good_status = good_status
        self.status_timeout = status_timeout
        self.message_pv = message_pv
        self.value = value
        self.wait = wait

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(CAActionPart, self).setup(registrar)
        # Hooks
        registrar.hook((builtin.hooks.InitHook,
                        builtin.hooks.ResetHook), self.connect_pvs)
        # Methods
        registrar.add_method_model(self.caput, self.name, self.description)

    def connect_pvs(self):
        pvs = [self.pv]
        if self.status_pv:
            pvs.append(self.status_pv)
        if self.message_pv:
            pvs.append(self.message_pv)
        ca_values = util.catools.caget(pvs)
        # check connection is ok
        for i, v in enumerate(ca_values):
            assert v.ok, "CA connect failed with %s" % v.state_strings[v.state]

    def wait_for_good_status(self, deadline):
        q = Queue()
        m = util.catools.camonitor(
            self.status_pv, q.put, datatype=util.catools.DBR_STRING)
        status = None
        try:
            while True:
                try:
                    status = q.get(deadline - time.time())
                except TimeoutError:
                    return status
                else:
                    if status == self.good_status:
                        return status
        finally:
            m.close()

    def caput(self):
        self.log.info("caput %s %s", self.pv, self.value)
        util.catools.caput(self.pv, self.value, wait=self.wait, timeout=None)
        if self.status_pv:
            # Wait for up to status_timeout for the right results to come in
            deadline = time.time() + self.status_timeout
            status = self.wait_for_good_status(deadline)
            if self.message_pv:
                message = " %s:" % util.catools.caget(
                    self.message_pv, datatype=util.catools.DBR_CHAR_STR)
            else:
                message = ""
            assert status == self.good_status, \
                "Status %s:%s while performing 'caput %s %s'" % (
                    status, message, self.pv, self.value)
