import pytest
from mock import call, MagicMock

from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.core import Context, Process
from malcolm.modules.ADOdin.parts import OdinWriterPart
from malcolm.modules.ADOdin.blocks import odin_writer_block
from malcolm.testutil import ChildTestCase


class TestOdinDWriterPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            odin_writer_block, self.process,
            mri="mri", prefix="prefix")
        self.o = OdinWriterPart(name="m", mri="mri")
        self.process.start()

        self.completed_steps = 0
        self.steps_to_do = 2000 * 3000
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3000, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2000)
        self.generator = CompoundGenerator([ys, xs], [], [], 0.1)
        self.generator.prepare()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_configure(self):
        self.o.configure(
            self.context, self.completed_steps, self.steps_to_do, {},
            generator=self.generator, fileDir='/tmp', fileName='odin.hdf')
        assert self.child.handled_requests.mock_calls == [
            call.put('fileName', 'odin.hdf'),
            call.put('filePath', '/tmp/'),
            call.put('numCapture', self.steps_to_do),
            call.post('start')]
        print(self.child.handled_requests.mock_calls)

    def test_run(self):
        self.o.configure(
            self.context, self.completed_steps, self.steps_to_do, {},
            generator=self.generator, fileDir='/tmp', fileName='odin.hdf')
        self.child.handled_requests.reset_mock()
        self.o.registrar = MagicMock()
        # run waits for this value
        self.child.field_registry.get_field("numCaptured").set_value(
            self.o.done_when_reaches)
        self.o.run(self.context)
        assert self.child.handled_requests.mock_calls == []
        assert self.o.registrar.report.called_once
        assert self.o.registrar.report.call_args_list[0][0][0].steps == \
               self.steps_to_do
