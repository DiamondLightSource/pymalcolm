from mock import Mock

from malcolm.modules.scanning.blocks import shutter_block
from malcolm.testutil import ChildTestCase


class TestShutterBlock(ChildTestCase):
    def test_shutter_block(self):
        self.create_child_block(
            shutter_block, Mock(), shutter_pv="shutter_pv", mri="mri"
        )
