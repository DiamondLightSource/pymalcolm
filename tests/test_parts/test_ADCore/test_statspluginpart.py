import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, ANY

from malcolm.parts.ADCore.statspluginpart import StatsPluginPart


class TestStatsPluginPart(unittest.TestCase):

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem

        self.params = MagicMock()
        self.process.get_block.return_value = self.child
        self.o = StatsPluginPart(self.process, self.params)

    def test_init(self):
        self.process.get_block.assert_called_once_with(self.params.child)
        self.assertEqual(self.o.child, self.child)

    def test_configure(self):
        task = MagicMock()
        completed_steps = ANY
        steps_to_do = ANY
        part_info = ANY
        self.o.configure(task, completed_steps, steps_to_do, part_info)
        task.put_many.assert_called_once_with(self.child, dict(
            enableCallbacks=True,
            computeStatistics=True))

if __name__ == "__main__":
    unittest.main(verbosity=2)
