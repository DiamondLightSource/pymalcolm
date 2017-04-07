import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, call, ANY
import time

from malcolm.core import Context, call_with_params
from malcolm.parts.ADCore.positionlabellerpart import PositionLabellerPart

from scanpointgenerator import LineGenerator, CompoundGenerator


class TestPositionLabellerPart(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock(spec=Context)
        self.o = call_with_params(
            PositionLabellerPart, name="pos", mri="BLOCK-POS")

    def test_configure(self):
        params = MagicMock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        params.generator = CompoundGenerator([ys, xs], [], [])
        params.generator.prepare()
        completed_steps = 2
        steps_to_do = 4
        part_info = ANY
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)
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
        assert self.context.mock_calls == [
            call.unsubscribe_all(),
            call.block_view('BLOCK-POS'),
            call.block_view().delete_async(),
            call.block_view().put_attribute_values_async(dict(
                enableCallbacks=True,
                idStart=3)),
            call.block_view().put_attribute_values_async().__radd__([ANY]),
            call.wait_all_futures(ANY),
            call.block_view().xml.put_value(expected_xml),
            call.block_view().start_async()]

    def test_run(self):
        update = MagicMock()
        self.o.start_future = MagicMock()
        self.o.run(self.context, update)
        assert self.context.mock_calls == [
            call.block_view('BLOCK-POS'),
            call.block_view().qty.subscribe_value(
                self.o.load_more_positions, ANY),
            call.wait_all_futures(self.o.start_future)]

    def test_load_more_positions(self):
        child = MagicMock()
        current_index = 1
        # Haven't done point 4 or 5 yet
        self.o.end_index = 4
        self.o.steps_up_to = 6
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        self.o.generator = CompoundGenerator([ys, xs], [], [])
        self.o.generator.prepare()
        self.o.load_more_positions(current_index, child)
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
        assert child.mock_calls == [call.xml.put_value(expected_xml)]
        assert self.o.end_index == 6


if __name__ == "__main__":
    unittest.main(verbosity=2)
