from mock import Mock

from malcolm.modules.ADSimDetector.blocks import sim_detector_runnable_block
from malcolm.testutil import ChildTestCase


class TestADSimDetectorBlocks(ChildTestCase):
    def test_sim_detector_runnable_block(self):
        c = self.create_child_block(
            sim_detector_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
        assert c.parts["label"].initial_value == "SimDetector"
