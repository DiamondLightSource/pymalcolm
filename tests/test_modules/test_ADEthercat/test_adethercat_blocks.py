from mock import Mock

from malcolm.modules.ADEthercat.blocks import ethercat_runnable_block
from malcolm.testutil import ChildTestCase


# The runnable block also contains the driver block
class TestADEthercatRunnableBlock(ChildTestCase):
    def test_ethercat_runnable_block(self):
        self.create_child_block(
            ethercat_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
