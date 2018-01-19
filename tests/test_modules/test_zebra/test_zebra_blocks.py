from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.zebra.blocks import zebra_driver_block, \
    zebra_runnable_block


class TestZebraBlocks(ChildTestCase):
    def test_zebra_driver_block(self):
        self.create_child_block(
            zebra_driver_block, Mock(),
            mri="mri", prefix="prefix")

    def test_zebra_runnable_block(self):
        self.create_child_block(
            zebra_runnable_block, Mock(),
            mri_prefix="mri_prefix", pv_prefix="pv_prefix", config_dir="/tmp")
