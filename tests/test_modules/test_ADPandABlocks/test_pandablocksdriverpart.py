import unittest
from mock import MagicMock, call

from malcolm.core import Context
from malcolm.modules.ADPandABlocks.parts import PandABlocksDriverPart


class TestPandaABoxDriverPart(unittest.TestCase):

    def setUp(self):
        self.child = MagicMock()
        self.context = MagicMock(spec=Context)
        self.context.block_view.return_value = self.child
        self.o = PandABlocksDriverPart(name="drv", mri="mri")

    def test_abort(self):
        self.o.abort(self.context)
        assert self.context.mock_calls == [
            call.block_view("mri"),
            call.block_view().stop(),
            call.block_view().when_value_matches(
                'acquiring', False, timeout=10.0)]

