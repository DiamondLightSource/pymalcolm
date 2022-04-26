from mock import Mock

from malcolm.modules.ADAndor3.blocks import ADAndor3_runnable_block
from malcolm.testutil import ChildTestCase


class TestADAndor3Blocks(ChildTestCase):
    def test_ADAndor3_runnable_block(self):
        self.create_child_block(
            ADAndor3_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
