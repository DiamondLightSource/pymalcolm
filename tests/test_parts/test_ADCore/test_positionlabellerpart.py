import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, call, ANY
import time

from malcolm.core import Task, SyncFactory
from malcolm.parts.ADCore.positionlabellerpart import PositionLabellerPart

from scanpointgenerator import LineGenerator, CompoundGenerator


class TestPositionLabellerPart(unittest.TestCase):

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem

        self.params = MagicMock()
        self.process.get_block.return_value = self.child
        self.o = PositionLabellerPart(self.process, self.params)

    def test_configure(self):
        task = MagicMock()
        params = MagicMock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        params.generator = CompoundGenerator([ys, xs], [], [])
        params.generator.prepare()
        completed_steps = 2
        steps_to_do = 4
        part_info = ANY
        self.o.configure(task, completed_steps, steps_to_do, part_info, params)
        self.assertEqual(task.post_async.call_args_list, [
                         call(self.child["delete"]),
                         call(self.child["start"])])
        task.put_many_async.assert_called_once_with(self.child, dict(
            enableCallbacks=True,
            idStart=3))
        expected_xml = """<?xml version="1.0" ?>
<pos_layout>
<dimensions>
<dimension name="d0" />
<dimension name="d1" />
<dimension name="FilePluginClose" />
</dimensions>
<positions>
<position FilePluginClose="0" d0="0" d1="2" />
<position FilePluginClose="0" d0="1" d1="2" />
<position FilePluginClose="0" d0="1" d1="1" />
<position FilePluginClose="1" d0="1" d1="0" />
</positions>
</pos_layout>""".replace("\n", "")
        task.put.assert_called_once_with(self.child["xml"], expected_xml)

    def test_run(self):
        task = MagicMock()
        update = MagicMock()
        self.o.start_future = MagicMock()
        self.o.run(task, update)
        task.subscribe.assert_called_once_with(
            self.child["qty"], self.o.load_more_positions, task)
        task.wait_all.assert_called_once_with(self.o.start_future)

    def test_load_more_positions(self):
        task = MagicMock()
        current_index = 1
        # Haven't done point 4 or 5 yet
        self.o.end_index = 4
        self.o.steps_up_to = 6
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        self.o.generator = CompoundGenerator([ys, xs], [], [])
        self.o.generator.prepare()
        self.o.load_more_positions(current_index, task)
        expected_xml = """<?xml version="1.0" ?>
<pos_layout>
<dimensions>
<dimension name="d0" />
<dimension name="d1" />
<dimension name="FilePluginClose" />
</dimensions>
<positions>
<position FilePluginClose="0" d0="1" d1="1" />
<position FilePluginClose="1" d0="1" d1="0" />
</positions>
</pos_layout>""".replace("\n", "")
        task.put.assert_called_once_with(self.child["xml"], expected_xml)
        self.assertEqual(self.o.end_index, 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
