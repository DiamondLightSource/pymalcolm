import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.parts.xspress3.xspress3driverpart import Xspress3DriverPart


class TestXspress3DetectorDriverPart(unittest.TestCase):

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem

        self.params = MagicMock()
        self.params.readoutTime = 0.002
        self.process.get_block.return_value = self.child
        self.o = Xspress3DriverPart(self.process, self.params)
        list(self.o.create_attributes())

    def test_configure(self):
        task = MagicMock()
        params = MagicMock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3000, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2000)
        params.generator = CompoundGenerator([ys, xs], [], [], 0.1)
        params.generator.prepare()
        completed_steps = 0
        steps_to_do = 2000*3000
        part_info = ANY
        self.o.configure(task, completed_steps, steps_to_do, part_info, params)
        self.assertEquals(task.put.call_count, 1)
        self.assertEquals(task.put.call_args_list[0],
                          call(self.child["pointsPerRow"], 15000))

if __name__ == "__main__":
    unittest.main(verbosity=2)
