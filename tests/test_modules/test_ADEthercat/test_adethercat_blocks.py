from mock import Mock

from malcolm.modules.ADEthercat.blocks import (
    ethercat_continuous_runnable_block,
    ethercat_hardware_runnable_block,
)
from malcolm.testutil import ChildTestCase


# The Reframe block also contains the driver block
class TestADEthercatReframeBlock(ChildTestCase):
    def test_ethercat_runnable_block(self):
        self.create_child_block(
            ethercat_hardware_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )


# The Continuous block also contains the driver block
class TestADEthercatContinuousBlock(ChildTestCase):
    def test_ethercat_runnable_block(self):
        self.create_child_block(
            ethercat_continuous_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
