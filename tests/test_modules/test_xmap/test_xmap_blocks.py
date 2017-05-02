from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.xmap.blocks import xmap_detector_manager_block


class TestXmapBlocks(ChildTestCase):
    def test_xmap_detector_manager_block(self):
        self.create_child_block(
            xmap_detector_manager_block, Mock(),
            mriPrefix="mriPrefix", pvPrefix="pvPrefix", configDir="/tmp")
