from malcolm.core import Process
from malcolm.modules.builtin.controllers import ManagerController
from malcolm.modules.pmac.blocks import pmac_status_block
from malcolm.modules.pmac.parts import PmacStatusPart
from malcolm.testutil import ChildTestCase


class TestPmacStatusPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        child = self.create_child_block(
            pmac_status_block, self.process, mri="my_mri", pv_prefix="PV:PRE"
        )
        self.set_attributes(child, i10=1705244)
        c = ManagerController("PMAC", "/tmp")
        self.o = PmacStatusPart(name="part", mri="my_mri", initial_visibility=True)
        c.add_part(self.o)
        self.process.add_controller(c)
        self.process.start()
        self.b = c.block_view()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_servo_freq(self):
        freq = self.b.servoFrequency()
        assert freq == 4919.300698316487
