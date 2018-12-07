from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.ADMerlin.blocks import merlin_runnable_block


class TestADMerlinBlocks(ChildTestCase):
    def test_merlin_detector_runnable_block(self):
        self.create_child_block(
            merlin_runnable_block, Mock(),
            mri_prefix="mri_prefix", pv_prefix="pv_prefix", config_dir="/tmp")
