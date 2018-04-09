from mock import MagicMock, ANY, call

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Context, Process
from malcolm.modules.ADCore.includes import adbase_parts
from malcolm.modules.ADCore.infos import ExposureDeadtimeInfo
from malcolm.modules.ADCore.parts import DetectorDriverPart
from malcolm.modules.builtin.controllers import StatefulController
from malcolm.testutil import ChildTestCase


class TestDetectorDriverPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)

        def child_block():
            controllers, parts = adbase_parts(prefix="prefix")
            controller = StatefulController("mri")
            for part in parts:
                controller.add_part(part)
            return controllers + [controller]

        self.child = self.create_child_block(child_block, self.process)
        self.o = DetectorDriverPart(
            name="m", mri="mri", is_hardware_triggered=False)
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_report(self):
        info = self.o.report_status()
        assert info.rank == 2

    def test_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2)
        generator = CompoundGenerator([ys, xs], [], [], 0.1)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 6
        part_info = dict(anyname=[ExposureDeadtimeInfo(0.01, 1000)])
        self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, generator)
        assert self.child.handled_requests.mock_calls == [
            call.put('arrayCallbacks', True),
            call.put('arrayCounter', 0),
            call.put('exposure', 0.1 - 0.01 - 0.0001),
            call.put('imageMode', 'Multiple'),
            call.put('numImages', 6)]

    def test_run(self):
        self.o.registrar = MagicMock()
        self.o.run(self.context)
        assert self.child.handled_requests.mock_calls == [
            call.post('start')]
        assert self.o.registrar.report.called_once
        assert self.o.registrar.report.call_args[0][0].steps == 0

    def test_abort(self):
        self.o.abort(self.context)
        assert self.child.handled_requests.mock_calls == [
            call.post('stop')]
