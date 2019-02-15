from mock import Mock

from malcolm.core import Context, Process
from malcolm.modules.pmac.parts import BrickPart
from malcolm.modules.pmac.blocks import brick_block
from malcolm.modules.scanning.hooks import ReportStatusHook
from malcolm.testutil import ChildTestCase


class TestBrickPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        child = self.create_child_block(
            brick_block, self.process, mri="my_mri", prefix="PV:PRE")
        self.set_attributes(child,
                            i10=1705244)
        self.o = BrickPart(name="part", mri="my_mri")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_init(self):
        registrar = Mock()
        self.o.setup(registrar)
        self.assert_hooked(self.o, ReportStatusHook, self.o.report_status)

    def test_report(self):
        returns = self.o.report_status(self.context)
        assert returns.i10 == 1705244
