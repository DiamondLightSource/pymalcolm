import unittest
from mock import MagicMock, call

from malcolm.core import Context
from malcolm.modules.ADPandABlocks.parts import PandABlocksDriverPart


class TestPandaABoxDriverPart(unittest.TestCase):

    def setUp(self):
        self.child = MagicMock()
        self.context = MagicMock(spec=Context)
        self.context.block_view.return_value = self.child
        self.params = MagicMock()
        self.params.name = "drv"
        self.params.mri = "mri"
        self.params.readoutTime = 0.002
        self.o = PandABlocksDriverPart(self.params)
        list(self.o.create_attribute_models())

    def test_abort(self):
        self.o.abort(self.context)
        assert self.context.mock_calls == [
            call.block_view("mri"),
            call.block_view().stop()]
