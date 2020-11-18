from mock import call
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import Context, Process
from malcolm.modules.adUtil.blocks import reframe_plugin_block
from malcolm.modules.adUtil.parts import ReframePluginPart
from malcolm.testutil import ChildTestCase


class TestReframePluginPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            reframe_plugin_block, self.process, mri="mri", prefix="prefix"
        )
        self.mock_when_value_matches(self.child)
        self.o = ReframePluginPart(name="m", mri="mri")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_report(self):
        infos = self.o.on_report_status()
        assert len(infos) == 1
        assert infos[0].rank == 2

    def test_validate(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 0.0002)
        generator.prepare()
        self.o.on_validate(generator)

    def test_validate_fails(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 0.00009)
        generator.prepare()
        with self.assertRaises(AssertionError):
            self.o.on_validate(generator)

    def test_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 0.1)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 6
        # We wait to be armed, so set this here
        self.set_attributes(self.child, acquiring=True)
        self.o.on_configure(
            self.context, completed_steps, steps_to_do, {}, generator, fileDir="/tmp"
        )
        assert self.child.handled_requests.mock_calls == [
            call.put("arrayCallbacks", True),
            call.put("arrayCounter", 0),
            call.put("imageMode", "Multiple"),
            call.put("numImages", 6),
            call.put("postCount", 999),
            call.post("start"),
            call.when_value_matches("acquiring", True, None),
        ]
