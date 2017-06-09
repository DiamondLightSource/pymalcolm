from mock import MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import call_with_params, Context, Process
from malcolm.modules.ADSimDetector.blocks import sim_detector_driver_block
from malcolm.modules.ADSimDetector.parts import SimDetectorDriverPart
from malcolm.testutil import ChildTestCase


class TestSimDetectorDriverPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            sim_detector_driver_block, self.process,
            mri="mri", prefix="prefix")
        self.o = call_with_params(
            SimDetectorDriverPart, name="m", mri="mri")
        list(self.o.create_attributes())
        self.process.start()

    def test_report(self):
        infos = self.o.report_configuration(ANY)
        assert len(infos) == 1
        assert infos[0].name == "m"
        assert infos[0].rank == 2

    def test_validate(self):
        params = MagicMock()
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        params.generator = CompoundGenerator([ys, xs], [], [], 0.1)
        params.generator.prepare()
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
        assert self.child.handled_requests.mock_calls == [
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            call.put('imageMode', 'Multiple'),
            call.put('numImages', 6),
            call.put('exposure', 0.1 - 7e-5)]

    def test_run(self):
        update_completed_steps = MagicMock()
        self.o.start_future = MagicMock()
        self.o.done_when_reaches = MagicMock()
        self.o.run(self.context, update_completed_steps)
        assert self.child.handled_requests.mock_calls == [
            call.post('start')]

    def test_abort(self):
        self.o.abort(self.context)
        assert self.child.handled_requests.mock_calls == [
            call.post('stop')]
