import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, ANY, call

from malcolm.core import Context
from malcolm.parts.ADPandABlocks import PandABlocksDriverPart


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
        list(self.o.create_attributes())

    def test_configure(self):
        completed_steps = 0
        steps_to_do = 6
        part_info = ANY
        self.o.configure(self.context, completed_steps, steps_to_do, part_info)
        assert self.context.mock_calls == [
            call.block_view("mri"),
            call.unsubscribe_all(),
            call.block_view().put_attribute_values(dict(
                imageMode="Multiple",
                numImages=steps_to_do,
                arrayCounter=completed_steps,
                arrayCallbacks=True)),
            call.block_view().start_async()]

    def test_run(self):
        update_completed_steps = MagicMock()
        self.o.start_future = MagicMock()
        self.o.run(self.context, update_completed_steps)
        assert self.context.mock_calls == [
            call.block_view("mri"),
            call.block_view().arrayCounter.subscribe_value(
                update_completed_steps, self.o),
            call.wait_all_futures(self.o.start_future)]

    def test_abort(self):
        self.o.abort(self.context)
        assert self.context.mock_calls == [
            call.block_view("mri"),
            call.block_view().stop()]


if __name__ == "__main__":
    unittest.main(verbosity=2)
