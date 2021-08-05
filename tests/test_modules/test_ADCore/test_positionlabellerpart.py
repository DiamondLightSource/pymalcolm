import numpy as np
from mock import MagicMock, call
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import Context, Future, Process
from malcolm.modules.ADCore.blocks import position_labeller_block
from malcolm.modules.ADCore.parts import PositionLabellerPart
from malcolm.modules.ADCore.util import FRAME_TIMEOUT
from malcolm.testutil import ChildTestCase


class TestPositionLabellerPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            position_labeller_block, self.process, mri="BLOCK-POS", prefix="prefix"
        )
        self.o = PositionLabellerPart(name="m", mri="BLOCK-POS")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

    def tearDown(self):
        self.process.stop(2)

    def test_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], duration=1.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 6

        self.o.on_configure(self.context, completed_steps, steps_to_do, generator)

        expected_xml = """<?xml version="1.0" ?>
<pos_layout>
<dimensions>
<dimension name="d0" />
<dimension name="d1" />
</dimensions>
<positions>
<position d0="0" d1="0" />
<position d0="0" d1="1" />
<position d0="0" d1="2" />
<position d0="1" d1="2" />
<position d0="1" d1="1" />
<position d0="1" d1="0" />
</positions>
</pos_layout>""".replace(
            "\n", ""
        )

        # Wait for the start_future so the post gets through to our child
        # even on non-cothread systems
        self.o.start_future.result(timeout=1)

        assert self.child.handled_requests.mock_calls == [
            call.post("delete"),
            call.put("arrayCounter", 0),
            call.put("enableCallbacks", True),
            call.put("idStart", 1),
            call.put("xml", expected_xml),
            call.post("start"),
        ]
        assert self.o.done_when_reaches == 6
        assert np.isclose(self.o.frame_timeout, FRAME_TIMEOUT + 1.0)

    def test_configure_zero_duration_doubles_frame_timeout(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], duration=0.0)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 6

        self.o.on_configure(self.context, completed_steps, steps_to_do, generator)

        # Wait for the start_future so the post gets through to our child
        # even on non-cothread systems
        self.o.start_future.result(timeout=1)

        assert np.isclose(self.o.frame_timeout, 2 * FRAME_TIMEOUT)

    def test_on_seek(self):
        # Set up the generator which would have been done in original configure
        xs = LineGenerator("x", "mm", 0.0, 0.5, 5, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 3)
        generator = CompoundGenerator([ys, xs], [], [], duration=1.0)
        generator.prepare()
        self.o.generator = generator

        # Now we can call on_seek
        completed_steps = 10
        steps_to_do = 5
        self.o.done_when_reaches = 10

        self.o.on_seek(self.context, completed_steps, steps_to_do)

        expected_xml = """<?xml version="1.0" ?>
<pos_layout>
<dimensions>
<dimension name="d0" />
<dimension name="d1" />
</dimensions>
<positions>
<position d0="2" d1="0" />
<position d0="2" d1="1" />
<position d0="2" d1="2" />
<position d0="2" d1="3" />
<position d0="2" d1="4" />
</positions>
</pos_layout>""".replace(
            "\n", ""
        )

        self.o.start_future.result(timeout=1)
        assert self.child.handled_requests.mock_calls == [
            call.post("delete"),
            call.put("arrayCounter", 10),
            call.put("enableCallbacks", True),
            call.put("idStart", 11),
            call.put("xml", expected_xml),
            call.post("start"),
        ]
        assert self.o.done_when_reaches == 15

    def test_run(self):
        # Say that we've returned from start
        self.o.start_future = Future(None)
        self.o.start_future.set_result(None)
        self.o.on_run(self.context)
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
</dimensions>
<positions>
<position d0="1" d1="1" />
<position d0="1" d1="0" />
</positions>
</pos_layout>""".replace(
            "\n", ""
        )
        assert child.mock_calls == [call.xml.put_value(expected_xml)]
        assert self.o.end_index == 6

    def test_on_post_run_armed(self):
        self.o.done_when_reaches = 100
        # Add a dummy subscription so we check it clears
        self.context.subscribe("BLOCK-POS", MagicMock())
        assert len(self.context._subscriptions) == 1

        self.o.on_post_run_armed(self.context, 50)

        assert len(self.context._subscriptions) == 0
        assert self.o.done_when_reaches == 150
