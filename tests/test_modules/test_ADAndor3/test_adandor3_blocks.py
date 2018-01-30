from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.ADAndor3.blocks import andor3_detector_runnable_block


class TestADAndor3Blocks(ChildTestCase):
    def test_andor_detector_runnable_block(self):
        self.create_child_block(
            andor3_detector_runnable_block, Mock(),
            mriPrefix="mriPrefix", pvPrefix="pvPrefix", configDir="/tmp")
