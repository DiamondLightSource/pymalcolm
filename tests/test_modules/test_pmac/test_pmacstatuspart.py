from mock import Mock

from malcolm.core import Context, Process, PartRegistrar
from malcolm.modules.pmac.parts import PmacStatusPart
from malcolm.modules.pmac.blocks import pmac_status_block
from malcolm.testutil import ChildTestCase


class TestPmacStatusPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        child = self.create_child_block(
            pmac_status_block, self.process, mri="my_mri", prefix="PV:PRE")
        self.set_attributes(child,
                            i10=1705244)
        self.o = PmacStatusPart(name="part", mri="my_mri")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()
        self.o.init(self.context)

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_setup(self):
        registrar = Mock(spec=PartRegistrar)
        self.o.setup(registrar)
        registrar.add_method_model.assert_called_once_with(
            self.o.servo_frequency, "servoFrequency")

    def test_servo_freq(self):
        freq = self.o.servo_frequency()
        assert freq == 4919.300698316487
