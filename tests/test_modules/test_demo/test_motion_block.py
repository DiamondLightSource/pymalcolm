import shutil
import unittest

from malcolm.core import Process
from malcolm.modules.builtin.defines import tmp_dir
from malcolm.modules.demo.blocks import motion_block


class TestMotionBlock(unittest.TestCase):
    def setUp(self):
        self.p = Process("proc")
        self.config_dir = tmp_dir("config_dir")
        for c in motion_block("mri", config_dir=self.config_dir.value):
            self.p.add_controller(c)
        self.p.start()
        self.b = self.p.block_view("mri")
        self.bx = self.p.block_view("mri:COUNTERX")
        self.by = self.p.block_view("mri:COUNTERY")

    def tearDown(self):
        self.p.stop()
        shutil.rmtree(self.config_dir.value)

    def test_move(self):
        assert self.bx.counter.value == 0
        self.b.xMove(32)
        assert self.bx.counter.value == 32
        assert self.by.counter.value == 0
        self.b.yMove(31)
        assert self.by.counter.value == 31
