from mock import Mock

from malcolm.modules.ADOdin.blocks import odin_runnable_block
from malcolm.testutil import ChildTestCase


class TestADOdinBlocks(ChildTestCase):
    def test_odin_detector_runnable_block(self):
        c = self.create_child_block(
            odin_runnable_block,
            Mock(),
            mri_prefix="mri_prefix",
            pv_prefix="pv_prefix",
            config_dir="/tmp",
        )
        assert c.parts["label"].initial_value == "Odin"
