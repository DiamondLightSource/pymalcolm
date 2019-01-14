from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.ADOdin.blocks import odin_runnable_block


class TestADOdinBlocks(ChildTestCase):
    def test_odin_detector_runnable_block(self):
        self.create_child_block(
            odin_runnable_block, Mock(),
            mri_prefix="mri_prefix", pv_prefix="pv_prefix", config_dir="/tmp")
