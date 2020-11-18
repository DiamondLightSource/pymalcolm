from mock import Mock

from malcolm.modules.zebra.blocks import zebra_driver_block, zebra_runnable_block
from malcolm.testutil import ChildTestCase


class TestZebraBlocks(ChildTestCase):
    def test_zebra_driver_block(self):
        self.create_child_block(zebra_driver_block, Mock(), mri="mri", prefix="prefix")

    def test_zebra_runnable_block(self):
        c = self.create_child_block(
            zebra_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
        assert c.parts["label"].initial_value == "Zebra"
