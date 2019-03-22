import os
import h5py
from datetime import datetime

from mock import call, MagicMock
from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Context, Process
from malcolm.modules.ADOdin.blocks import odin_writer_block
from malcolm.modules.ADOdin.parts import OdinWriterPart
from malcolm.testutil import ChildTestCase
from tempfile import mkdtemp
from shutil import rmtree


class TestOdinWriterPart(ChildTestCase):
    EXCALIBUR_FILE_PATH = \
        os.path.join(os.path.join(os.path.dirname(
            os.path.realpath(__file__)), 'data'), 'test-EXCALIBUR.h5')

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            odin_writer_block, self.process,
            mri="mri", prefix="prefix")
        # set up some values for OdinData PVs that Excalibur would have
        settings = {
            'imageHeight': 1536,
            'imageWidth': 1048,
            'blockSize': 1,
            'numProcesses': 4,
            'dataType': 'uint16',
        }
        self.set_attributes(self.child, **settings)
        self.o = OdinWriterPart(name="m", mri="mri")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

        self.completed_steps = 0
        # goal for these is 3000, 2000, True
        cols, rows, alternate = 3000, 2000, False
        self.steps_to_do = cols * rows
        xs = LineGenerator("x", "mm", 0.0, 0.5, cols, alternate=alternate)
        ys = LineGenerator("y", "mm", 0.0, 0.1, rows)
        self.generator = CompoundGenerator([ys, xs], [], [], 0.1)
        self.generator.prepare()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_configure(self):
        tmp_dir = mkdtemp() + os.path.sep
        vds_file = 'odin2'

        start_time = datetime.now()
        self.o.configure(
            self.context, self.completed_steps, self.steps_to_do,
            generator=self.generator, fileDir=tmp_dir, formatName=vds_file)
        assert self.child.handled_requests.mock_calls == [
            call.put('fileName', 'odin2_raw_data'),
            call.put('filePath', tmp_dir),
            call.put('numCapture', self.steps_to_do),
            call.post('start')]
        print(self.child.handled_requests.mock_calls)
        print('OdinWriter configure {} points took {} secs'.format(
            self.steps_to_do, datetime.now() - start_time))
        #rmtree(tmp_dir)

    def test_run(self):
        tmp_dir = mkdtemp() + os.path.sep
        self.o.configure(
            self.context, self.completed_steps, self.steps_to_do,
            generator=self.generator, fileDir=tmp_dir, formatName='odin2',
            fileTemplate='a_unique_name_%s_from_gda.h5')
        self.child.handled_requests.reset_mock()
        self.o.registrar = MagicMock()
        # run waits for this value
        self.child.field_registry.get_field("numCaptured").set_value(
            self.o.done_when_reaches)
        self.o.run(self.context)
        assert self.child.handled_requests.mock_calls == [
            call.when_values_matches(
                'numCaptured', self.steps_to_do, None, None, 60)]
        assert self.o.registrar.report.called_once
        assert self.o.registrar.report.call_args_list[0][0][0].steps == \
            self.steps_to_do
        rmtree(tmp_dir)

    def test_alternate_fails(self):
        cols, rows, alternate = 3000, 2000, True
        self.steps_to_do = cols * rows
        xs = LineGenerator("x", "mm", 0.0, 0.5, cols, alternate=alternate)
        ys = LineGenerator("y", "mm", 0.0, 0.1, rows)
        self.generator = CompoundGenerator([ys, xs], [], [], 0.1)
        self.generator.prepare()

        self.assertRaises(
            ValueError, self.o.configure,
            *(self.context, self.completed_steps, self.steps_to_do),
            **{'generator': self.generator,
               'fileDir': '/tmp', 'formatName': 'odin3'})


