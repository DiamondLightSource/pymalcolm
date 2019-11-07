from mock import Mock

from malcolm.testutil import ChildTestCase
from malcolm.modules.scanning.blocks import shutter_block


class TestShutterBlock(ChildTestCase):
    def test_shutter_block(self):
        c = self.create_child_block(
            shutter_block, Mock(),
            shutter_pv="shutter_pv",
            mri="mri")
