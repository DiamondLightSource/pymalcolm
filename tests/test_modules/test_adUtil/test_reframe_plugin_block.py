from mock import Mock

from malcolm.modules.adUtil.blocks import reframe_plugin_block
from malcolm.testutil import ChildTestCase


class TestReframePluginBlock(ChildTestCase):
    def test_reframe_plugin_block(self):
        self.create_child_block(
            reframe_plugin_block,
            Mock(),
            mri="mri",
            prefix="prefix",
        )
