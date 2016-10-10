import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, ANY

from scanpointgenerator import LineGenerator, CompoundGenerator
from scanpointgenerator.fixeddurationmutator import FixedDurationMutator
from malcolm.parts.ADCore.detectordriverpart import DetectorDriverPart


class TestSimDetectorDriverPart(unittest.TestCase):

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem

        self.params = MagicMock()
        self.process.get_block.return_value = self.child
        self.o = DetectorDriverPart(self.process, self.params)
        list(self.o.create_attributes())

    def test_init(self):
        self.process.get_block.assert_called_once_with(self.params.child)
        self.assertEqual(self.o.child, self.child)

    def test_configure(self):
        task = MagicMock()
        params = MagicMock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate_direction=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        duration = FixedDurationMutator(0.1)
        params.generator = CompoundGenerator([ys, xs], [], [duration])
        completed_steps = 0
        steps_to_do = 6
        part_info = ANY
        self.o.configure(task, completed_steps, steps_to_do, part_info, params)
        task.put.assert_called_once_with({
            self.child["exposure"]: 0.1 - 0.002,
            self.child["imageMode"]: "Multiple",
            self.child["numImages"]: steps_to_do,
            self.child["arrayCounter"]: completed_steps,
            self.child["arrayCallbacks"]: True,
        })
        list(self.o.create_attributes())

    def test_run(self):
        task = MagicMock()
        self.o.run(task, ANY)
        task.post.assert_called_once_with(self.child["start"])

    def test_abort(self):
        task = MagicMock()
        self.o.abort(task)
        task.post.assert_called_once_with(self.child["stop"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
