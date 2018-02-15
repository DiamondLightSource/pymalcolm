from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.xmap.blocks import xmap_runnable_block


class TestXmapBlocks(ChildTestCase):
    def test_xmap_detector_manager_block(self):
        self.create_child_block(
            xmap_runnable_block, Mock(),
            mri_prefix="mri_prefix", pv_prefix="pv_prefix", config_dir="/tmp")
