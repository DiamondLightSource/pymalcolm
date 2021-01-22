from mock import Mock

from malcolm.modules.ADMerlin.blocks import merlin_runnable_block
from malcolm.testutil import ChildTestCase


class TestADMerlinBlocks(ChildTestCase):
    def test_merlin_detector_runnable_block(self):
        c = self.create_child_block(
            merlin_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
        assert c.parts["label"].initial_value == "Merlin"
