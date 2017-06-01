from mock import MagicMock, call, ANY

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Context, call_with_params, Process, Future
from malcolm.modules.ADCore.blocks import position_labeller_block
from malcolm.modules.ADCore.parts import PositionLabellerPart
from malcolm.testutil import ChildTestCase


class TestPositionLabellerPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            position_labeller_block, self.process,
            mri="BLOCK-POS", prefix="prefix")
        self.o = call_with_params(
            PositionLabellerPart, name="m", mri="BLOCK-POS")
        list(self.o.create_attributes())
        self.process.start()

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
        # Need to wait for the spawned mock start call to run
        self.o.start_future.result()
        assert self.child.handled_requests.mock_calls == [
            call.post('delete'),
            call.put('enableCallbacks', True),
            call.put('idStart', 3),
            call.put('xml', expected_xml),
            call.post('start')]

    def test_run(self):
        update = MagicMock()
        # Say that we've returned from start
        self.o.start_future = Future(None)
        self.o.start_future.set_result(None)
        self.o.run(self.context, update)
        assert update.mock_calls == []
        assert self.child.handled_requests.mock_calls == []

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
