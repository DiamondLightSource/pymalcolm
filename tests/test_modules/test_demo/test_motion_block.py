import unittest

from malcolm.core import Process
from malcolm.modules.demo.blocks import motion_block


class TestMotionBlock(unittest.TestCase):
    def setUp(self):
        self.p = Process("proc")
        for c in motion_block("mri", config_dir="/tmp"):
            self.p.add_controller(c)
        self.p.start()
        self.b = self.p.block_view("mri")
        self.bx = self.p.block_view("mri:COUNTERX")
        self.by = self.p.block_view("mri:COUNTERY")

    def tearDown(self):
        self.p.stop()

    def test_move(self):
        assert self.bx.counter.value == 0
        self.b.xMove(32)
        assert self.bx.counter.value == 32
        assert self.by.counter.value == 0
        self.b.yMove(31)
        assert self.by.counter.value == 31
