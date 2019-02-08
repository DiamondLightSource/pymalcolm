from mock import MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Context, Process
from malcolm.modules.adUtil.blocks import reframe_plugin_block
from malcolm.modules.adUtil.parts import ReframePluginPart
from malcolm.testutil import ChildTestCase


class TestReframePluginPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            reframe_plugin_block, self.process,
            mri="mri", prefix="prefix")
        self.o = ReframePluginPart(name="m", mri="mri")
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_report(self):
        infos = self.o.report_status()
        assert infos.rank == 2

    def test_validate(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 0.0002)
        generator.prepare()
        self.o.validate(generator)

    def test_validate_fails(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 0.00009)
        generator.prepare()
        with self.assertRaises(AssertionError):
            self.o.validate(generator)

    def test_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 0.1)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 6
        # We wait to be armed, so set this here
        self.set_attributes(self.child, acquiring=True)
        self.o.configure(
            self.context, completed_steps, steps_to_do, {}, generator)
        assert self.child.handled_requests.mock_calls == [
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            call.put('imageMode', 'Multiple'),
            call.put('numImages', 6),
            call.put('postCount', 999),
            call.post('start'),
            call.when_values_matches('acquiring', True, None, 10.0, None)]
