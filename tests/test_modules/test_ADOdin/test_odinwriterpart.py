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

from vdsgen import SubFrameVDSGenerator, InterleaveVDSGenerator, ExcaliburGapFillVDSGenerator, ReshapeVDSGenerator, generate_raw_files
import numpy as np


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
            call.put('fileName', 'odin2_raw_data.hdf'),
            call.put('filePath', tmp_dir),
            call.put('numCapture', self.steps_to_do),
            call.post('start')]
        print(self.child.handled_requests.mock_calls)
        print('OdinWriter configure {} points took {} secs'.format(
            self.steps_to_do, datetime.now() - start_time))
        rmtree(tmp_dir)

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


    def test_excalibur_vds(self):
        # Create a generator to match the test data
        line1 = LineGenerator('stage1_y', 'mm', -0.755, -0.754, 2)
        line2 = LineGenerator('stage1_x', 'mm', 11.45, 11.451, 2)
        compound = CompoundGenerator([line1, line2], [], [])
        compound.prepare()

        file_dir = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), 'data')

        # Call configure to create the VDS
        # This should work with relative paths but doesn't due to VDS bug
        self.o.configure(compound, file_dir, fileTemplate="test-%s.h5")

        # Open the created VDS file and dataset to check values
        vds_file = h5py.File(self.EXCALIBUR_FILE_PATH, "r")
        detector_dataset = vds_file['/entry/detector/detector']

        # Check values at indices 0,0
        assert detector_dataset[0][0][756][393] == 0
        assert detector_dataset[0][0][756][394] == 3
        assert detector_dataset[0][0][756][395] == 2
        assert detector_dataset[0][0][756][396] == 1

        # Change first index
        assert detector_dataset[1][0][756][393] == 0
        assert detector_dataset[1][0][756][394] == 1
        assert detector_dataset[1][0][756][395] == 3
        assert detector_dataset[1][0][756][396] == 0

        # Change second index
        assert detector_dataset[0][1][756][393] == 0
        assert detector_dataset[0][1][756][394] == 0
        assert detector_dataset[0][1][756][395] == 3
        assert detector_dataset[0][1][756][396] == 3

        # Check some values near the bottom of image to ensure
        # the gaps are there
        assert detector_dataset[0][0][1685][1521] == 3
        assert detector_dataset[1][0][1685][1521] == 131

        assert detector_dataset[0][0][1516][329] == 109
        assert detector_dataset[0][1][1516][329] == 136

        # Check some values in the gaps
        assert detector_dataset[0][0][395][1202] == 0
        assert detector_dataset[1][0][395][1202] == 0

        # Check detector attributes
        detector_group = vds_file['/entry/detector']
        assert detector_group.attrs['axes'] == 'stage1_y_set,stage1_x_set,.,.'
        assert detector_group.attrs['signal'] == 'detector'
        assert detector_group.attrs['stage1_y_set_indices'] == '0'
        assert detector_group.attrs['stage1_x_set_indices'] == '1'

        # Check _set datasets
        # N.B. units are encoded as ASCII in the original file, so come
        # back as type byte in Python 3
        stage1_x_set_dataset = vds_file['/entry/detector/stage1_x_set']
        assert stage1_x_set_dataset[0] == 11.45
        assert stage1_x_set_dataset[1] == 11.451
        assert stage1_x_set_dataset.attrs['units'] == b'mm'

        stage1_y_set_dataset = vds_file['/entry/detector/stage1_y_set']
        assert stage1_y_set_dataset[0] == -0.755
        assert stage1_y_set_dataset[1] == -0.754
        assert stage1_y_set_dataset.attrs['units'] == b'mm'

        vds_file.close()
