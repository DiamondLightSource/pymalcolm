import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock

from malcolm.parts.pmac.rawmotorpart import RawMotorPart


class TestRawMotorPart(unittest.TestCase):

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()
        self.params = MagicMock()
        self.process.get_block.return_value = self.child
        self.c = RawMotorPart(self.process, self.params)

    def test_init(self):
        self.process.get_block.assert_called_once_with(self.params.child)
        self.assertEqual(self.c.child, self.child)

    def test_report(self):
        returns = self.c.report_cs_info(None, MagicMock())
        self.assertEqual(returns.cs_axis, self.child.cs_axis)
        self.assertEqual(returns.cs_port, self.child.cs_port)
        self.assertEqual(returns.acceleration_time, self.child.acceleration_time)
        self.assertEqual(returns.resolution, self.child.resolution)
        self.assertEqual(returns.offset, self.child.offset)
        self.assertEqual(returns.max_velocity, self.child.max_velocity)
        self.assertEqual(returns.current_position, self.child.position)


if __name__ == "__main__":
    unittest.main(verbosity=2)
