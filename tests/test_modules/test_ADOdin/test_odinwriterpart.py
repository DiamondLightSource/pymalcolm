import pytest
from mock import call

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

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_configure(self):
        xs = LineGenerator("x", "mm", 0.0, 0.5, 3000, alternate=True)
        ys = LineGenerator("y", "mm", 0.0, 0.1, 2000)
        generator = CompoundGenerator([ys, xs], [], [], 0.1)
        generator.prepare()
        completed_steps = 0
        steps_to_do = 2000 * 3000

        self.o.configure(
            self.context, completed_steps, steps_to_do, {}, generator=generator,
            fileDir='/tmp', fileName='odin.hdf')
        assert self.child.handled_requests.mock_calls == [
            call.put('fileName', 'odin.hdf'),
            call.put('filePath', '/tmp/'),
            call.put('numCapture', 6000000),
            call.post('start')]
        print(self.child.handled_requests.mock_calls)
