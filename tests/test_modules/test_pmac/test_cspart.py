from malcolm.core import Context, Process
from malcolm.modules.pmac.parts import CSPart
from malcolm.modules.pmac.blocks import cs_block
from malcolm.testutil import ChildTestCase


class TestCSPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            cs_block, self.process, mri="PMAC:CS1",
            prefix="PV:PRE")
        self.set_attributes(self.child, port="CS1")
        self.o = CSPart(name="pmac", mri="PMAC:CS1")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_report_status(self):
        info = self.o.report_status(self.context)
        assert info.mri == "PMAC:CS1"
        assert info.port == "CS1"
