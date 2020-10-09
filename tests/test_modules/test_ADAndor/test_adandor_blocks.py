from mock import Mock

from malcolm.modules.ADAndor.blocks import andor_runnable_block
from malcolm.testutil import ChildTestCase


class TestADAndorBlocks(ChildTestCase):
    def test_andor_detector_runnable_block(self):
        self.create_child_block(
            andor_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
