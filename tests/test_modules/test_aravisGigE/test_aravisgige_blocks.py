from mock import Mock

from malcolm.modules.aravisGigE.blocks import aravisGigE_runnable_block
from malcolm.testutil import ChildTestCase


class TestXmapBlocks(ChildTestCase):
    def test_xmap_detector_manager_block(self):
        c = self.create_child_block(
            aravisGigE_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
        assert c.parts["label"].initial_value == "aravisGigE"
