from mock import Mock

from malcolm.modules.ADTucsen.blocks import tucsen_runnable_block
from malcolm.testutil import ChildTestCase


class TestADTucsenBlocks(ChildTestCase):
    def test_tucsen_runnable_block(self):
        self.create_child_block(
            tucsen_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
