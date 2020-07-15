from mock import Mock

from malcolm.modules.ADPandABlocks.blocks import panda_runnable_block
from malcolm.testutil import ChildTestCase


class TestADPandABlocksBlocks(ChildTestCase):
    def test_pandablocks_runnable_block(self):
        c = self.create_child_block(
            panda_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
        assert c.parts["label"].initial_value == "PandA"
