from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.ADAndor.blocks import andor_detector_manager_block


class TestADAndorBlocks(ChildTestCase):
    def test_pandablocks_runnable_block(self):
        self.create_child_block(
            andor_detector_manager_block, Mock(),
            mriPrefix="mriPrefix", pvPrefix="pvPrefix", configDir="/tmp")
