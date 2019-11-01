from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.scanning.blocks import shutter_block
from malcolm.modules.ca.parts.cachoicepart import CAChoicePart


class TestShutterBlock(ChildTestCase):
    def test_shutter_block(self):
        c = self.create_child_block(
            shutter_block, Mock(),
            shutter_pv="shutter_pv",
            mri="mri",
            config_dir="/tmp")
        self.assertIsInstance(c.parts["shutter"], CAChoicePart)
