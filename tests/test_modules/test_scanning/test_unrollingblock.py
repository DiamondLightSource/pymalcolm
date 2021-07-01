from mock import Mock

from malcolm.modules.scanning.blocks import unrolling_block
from malcolm.testutil import ChildTestCase


class TestUnrollingBlock(ChildTestCase):
    def test_unrolling_block(self):
        self.create_child_block(
            unrolling_block,
            Mock(),
            mri="TEST:MRI",
        )
