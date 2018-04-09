from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.excalibur.blocks import excalibur_runnable_block


class TestExcaliburBlocks(ChildTestCase):
    def test_blocks(self):
        self.create_child_block(
            excalibur_runnable_block, Mock(),
            mri_prefix="mri_prefix", pv_prefix="pv_prefix", config_dir="/tmp")
