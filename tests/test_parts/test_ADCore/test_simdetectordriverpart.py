import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock

from malcolm.parts.ADCore.simdetectordriverpart import SimDetectorDriverPart


class TestSimDetectorDriverPart(unittest.TestCase):

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem

        self.params = MagicMock()
        self.process.get_block.return_value = self.child
        self.o = SimDetectorDriverPart(self.process, self.params)

    def test_init(self):
        self.process.get_block.assert_called_once_with(self.params.child)
        self.assertEqual(self.o.child, self.child)

    def test_configure(self):
        task = MagicMock()
        params = MagicMock()
        self.o.configure(task, params)
        task.put.assert_called_once_with({
            self.child["exposure"]: params.exposure,
            self.child["imageMode"]: "Multiple",
            self.child["numImages"]: params.generator.num,
            self.child["arrayCounter"]: params.start_step,
            self.child["arrayCallbacks"]: True,
        })

    def test_run(self):
        task = MagicMock()
        self.o.run(task)
        task.post.assert_called_once_with(self.child["start"])

    def test_abort(self):
        task = MagicMock()
        self.o.abort(task)
        task.post.assert_called_once_with(self.child["stop"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
