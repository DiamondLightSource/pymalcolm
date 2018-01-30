from mock import MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import call_with_params, Context, Process
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
        choices = ["Single", "Multiple", "Continuous"]
        self.child.parts["imageMode"].attr.meta.set_choices(choices)
        self.o = call_with_params(
            ReframePluginPart, name="m", mri="mri")
        list(self.o.create_attribute_models())
        self.process.start()

    def test_report(self):
        infos = self.o.report_configuration(self.context)
        assert len(infos) == 2
        assert infos[0].value == 0
        assert infos[1].rank == 2

    def test_validate(self):
        params = MagicMock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        params.generator = CompoundGenerator([ys, xs], [], [], 0.0002)
        params.generator.prepare()
        self.o.validate(ANY, ANY, params)

    def test_validate_fails(self):
        params = MagicMock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        params.generator = CompoundGenerator([ys, xs], [], [], 0.00009)
        params.generator.prepare()
        with self.assertRaises(AssertionError):
            self.o.validate(ANY, ANY, params)

    def test_configure(self):
        params = MagicMock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        params.generator = CompoundGenerator([ys, xs], [], [], 0.1)
        params.generator.prepare()
        completed_steps = 0
        steps_to_do = 6
        part_info = ANY
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)
        # Need to wait for the spawned mock start call to run
        self.o.start_future.result()
        assert self.child.handled_requests.mock_calls == [
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            call.put('imageMode', 'Multiple'),
            call.put('numImages', 6),
            call.put('postCount', 999),
            call.post('start')]
