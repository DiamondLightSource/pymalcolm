from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.ADEiger.blocks import eiger_runnable_block


class TestADEigerBlocks(ChildTestCase):
    def test_eiger_detector_runnable_block(self):
        self.create_child_block(
            eiger_runnable_block, Mock(),
            mri_prefix="mri_prefix", pv_prefix="pv_prefix", config_dir="/tmp")

