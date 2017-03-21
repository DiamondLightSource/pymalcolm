import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, ANY, call

from malcolm.parts.pandabox.pandaboxdriverpart import PandABoxDriverPart


class TestPandaABoxDriverPart(unittest.TestCase):

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem

        self.params = MagicMock()
        self.params.readoutTime = 0.002
        self.process.get_block.return_value = self.child
        self.o = PandABoxDriverPart(self.process, self.params)
        list(self.o.create_attributes())

    def test_configure(self):
        task = MagicMock()
        completed_steps = 0
        steps_to_do = 6
        part_info = ANY
        self.o.configure(task, completed_steps, steps_to_do, part_info)
        task.put_many.assert_called_once_with(self.child, dict(
            imageMode="Multiple",
            numImages=steps_to_do,
            arrayCounter=completed_steps,
            arrayCallbacks=True))
        task.post_async.assert_called_once_with(self.child["start"])

    def test_run(self):
        task = MagicMock()
        update_completed_steps = MagicMock()
        self.o.start_future = MagicMock()
        self.o.run(task, update_completed_steps)
        task.subscribe.assert_called_once_with(
            self.child["arrayCounter"], update_completed_steps, self.o)
        task.wait_all.assert_called_once_with(self.o.start_future)

    def test_abort(self):
        task = MagicMock()
        self.o.abort(task)
        task.post.assert_called_once_with(self.child["stop"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
