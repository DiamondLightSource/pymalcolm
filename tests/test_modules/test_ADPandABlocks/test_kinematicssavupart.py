import os
import glob
import numpy as np
from datetime import datetime
from shutil import rmtree, copy
from tempfile import mkdtemp

import h5py
from mock import call, MagicMock
from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.core import Context, Process
from malcolm.modules.ADPandABlocks.blocks import panda_kinematicssavu_block
from malcolm.modules.ADPandABlocks.parts.kinematicssavupart \
    import KinematicsSavuPart
from malcolm.modules.builtin.controllers import ManagerController
from malcolm.modules.scanning.infos import DatasetProducedInfo, DatasetType
from malcolm.testutil import ChildTestCase
from malcolm.yamlutil import make_block_creator
from tests.test_modules.test_ADPandABlocks.test_pandaseqtriggerpart import \
    PositionsPart


class TestKinematicsSavuPart(ChildTestCase):
    def setUp(self):

        self.process = Process("Process")
        self.context = Context(self.process)

        # Create a fake PandA
        self.panda = ManagerController("PANDA", "/tmp")
        self.busses = PositionsPart("busses")
        self.panda.add_part(self.busses)

        # And the PMAC
        pmac_block = make_block_creator(
            os.path.join(os.path.dirname(__file__), "..", "test_pmac", "blah"),
            "test_pmac_manager_block.yaml")
        self.pmac = self.create_child_block(
            pmac_block, self.process, mri_prefix="PMAC",
            config_dir="/tmp")
        # These are the motors we are interested in
        self.child_x = self.process.get_controller("BL45P-ML-STAGE-01:X")
        self.child_y = self.process.get_controller("BL45P-ML-STAGE-01:Y")
        self.child_cs1 = self.process.get_controller("PMAC:CS1")
        # CS1 needs to have the right port otherwise we will error
        self.set_attributes(self.child_cs1, port="CS1")

        # Make the child block holding panda and pmac mri
        self.child = self.create_child_block(
            panda_kinematicssavu_block, self.process,
            mri="SCAN:KINSAV", panda="PANDA", pmac="PMAC")

        self.o = KinematicsSavuPart(name="kinsav", mri="SCAN:KINSAV")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()
        self.set_attributes(self.pmac)

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

    def set_motor_attributes(
            self, x_pos=0.5, y_pos=0.0, units="mm",
            x_acceleration=2.5, y_acceleration=2.5,
            x_velocity=1.0, y_velocity=1.0):
        # create some parts to mock the motion controller and 2 axes in a CS
        self.set_attributes(
            self.child_x, cs="CS1,A",
            accelerationTime=x_velocity/x_acceleration, resolution=0.001,
            offset=0.0, maxVelocity=x_velocity, readback=x_pos,
            velocitySettle=0.0, units=units, axisNumber=1)
        self.set_attributes(
            self.child_y, cs="CS1,B",
            accelerationTime=y_velocity/y_acceleration, resolution=0.001,
            offset=0.0, maxVelocity=y_velocity, readback=y_pos,
            velocitySettle=0.0, units=units, axisNumber=23)

    def test_configure(self):
        tmp_dir = mkdtemp() + os.path.sep
        vds_file = 'odin2'
        self.set_motor_attributes(0.5, 0.0, "mm")

        start_time = datetime.now()
        self.o.configure(
            self.context, fileDir=tmp_dir, axesToMove=['x', 'y'], formatName=vds_file)
        #assert self.child.handled_requests.mock_calls == [
        #    call.put('fileName', 'odin2_raw_data'),
        #    call.put('filePath', tmp_dir),
        #    call.put('numCapture', self.steps_to_do),
        #    call.post('start')]

        self.o.post_configure(self.context)

        print(self.child.handled_requests.mock_calls)
        print('KinematicsSavu configure {} points took {} secs'.format(
            self.steps_to_do, datetime.now() - start_time))
        rmtree(tmp_dir)

    def test_file_creation(self):
        tmp_dir = mkdtemp() + os.path.sep
        data_name = 'odin2'
        self.set_motor_attributes(0.5, 0.0, "mm")

        start_time = datetime.now()
        self.o.configure(
            self.context, fileDir=tmp_dir, axesToMove=['x', 'y'], formatName=data_name)
        #assert self.child.handled_requests.mock_calls == [
        #    call.put('fileName', 'odin2_raw_data'),
        #    call.put('filePath', tmp_dir),
        #    call.put('numCapture', self.steps_to_do),
        #    call.post('start')]

        part_info = dict(
            HDF=[
                DatasetProducedInfo("y.data", "kinematics_PANDABOX.h5", DatasetType.POSITION_VALUE, 2,
                                    "/entry/NDAttributes/INENC1.VAL", "/p/uid"),
                DatasetProducedInfo("x.data", "kinematics_PANDABOX2.h5", DatasetType.POSITION_VALUE, 0,
                                    "/entry/NDAttributes/INENC1.VAL", "/p/uid"),
                DatasetProducedInfo("y.max", "kinematics_PANDABOX.h5", DatasetType.POSITION_MAX, 0,
                                    "/entry/NDAttributes/INENC1_MAX.VAL", "/p/uid"),
                DatasetProducedInfo("y.min", "kinematics_PANDABOX.h5", DatasetType.POSITION_MIN, 0,
                                    "/entry/NDAttributes/INENC1_MIN.VAL", "/p/uid"),
                DatasetProducedInfo("x.max", "kinematics_PANDABOX2.h5", DatasetType.POSITION_MAX, 0,
                                    "/entry/NDAttributes/INENC1_MAX.VAL", "/p/uid"),
                DatasetProducedInfo("x.min", "kinematics_PANDABOX2.h5", DatasetType.POSITION_MIN, 0,
                                    "/entry/NDAttributes/INENC1_MIN.VAL", "/p/uid"),
                DatasetProducedInfo("det.min", "fn1", DatasetType.SECONDARY, 0,
                                    "/p/s2", "/p/uid"),
            ]
        )

        self.o.post_configure(self.context, part_info)

        self.o.post_run_ready(self.context)

        # Check Savu file has been created and contains the correct entries
        savu_path = os.path.join(tmp_dir, data_name + '.nxs')
        savu_file = h5py.File(savu_path, "r")

        # Check the forward kinematics program has been written
        program_dataset = savu_file['/entry/inputs/program']
        self.assertEquals(program_dataset.shape, (3, ))
        self.assertEquals(program_dataset[0], "Q1=P1+10")

        # Check the Q and I program variables have been written
        variables_dataset = savu_file['/entry/inputs/variables']
        self.assertEquals(variables_dataset.shape, (2, ))
        name = variables_dataset[0][0]
        val = variables_dataset[0][1]
        self.assertEquals(name, 'Q22')
        self.assertEquals(val, 12345)

        # Check the p1 datasets have been written
        # Create raw data file first that the file will link to
        raw_path = os.path.join(tmp_dir, 'kinematics_PANDABOX2.h5')
        raw = h5py.File(raw_path, "w")
        raw.require_group('/entry/NDAttributes/')
        fmnd_mean = np.zeros((5, 5, 1, 1))
        fmnd_mean[0][0][0][0] = 61616
        fmnd_mean[1][2][0][0] = 10101
        raw.create_dataset('/entry/NDAttributes/INENC1.VAL', data=fmnd_mean)
        fmnd_max = np.zeros((5, 5, 1, 1))
        fmnd_max[0][0][0][0] = 27
        fmnd_max[3][4][0][0] = 18
        raw.create_dataset('/entry/NDAttributes/INENC1_MAX.VAL', data=fmnd_max)
        raw.close()

        # Check p1 mean and max datasets are there
        p1mean_dataset = savu_file['/entry/inputs/p1mean']
        self.assertEquals(p1mean_dataset.shape, (5, 5, 1, 1))
        self.assertEquals(p1mean_dataset[0][0][0][0], 61616)
        self.assertEquals(p1mean_dataset[1][2][0][0], 10101)
        p1max_dataset = savu_file['/entry/inputs/p1max']
        self.assertEquals(p1max_dataset.shape, (5, 5, 1, 1))
        self.assertEquals(p1max_dataset[0][0][0][0], 27)
        self.assertEquals(p1max_dataset[3][4][0][0], 18)
        savu_file.close()

        # Check the final vds file has been created
        # First create a fake Savu output file that the vds will link to
        raw_savu_path = os.path.join(tmp_dir, 'savuproc')
        os.mkdir(raw_savu_path)
        raw_savu_path = os.path.join(raw_savu_path, data_name + '_processed.nxs')
        raw_savu = h5py.File(raw_savu_path, "w")
        raw_savu.require_group('/entry/final_result_qmean/')
        savu_proc = np.ones((9, 5, 5))
        savu_proc[0][0][0] = 555
        savu_proc[0][2][1] = 666
        raw_savu.create_dataset('/entry/final_result_qmean/data', data=savu_proc)
        raw_savu.close()

        # Check q1mean is there
        vds_path = os.path.join(tmp_dir, data_name + '_vds.nxs')
        vds_file = h5py.File(vds_path, "r")
        q1mean = vds_file['/entry/q1mean']
        self.assertEquals(q1mean.shape, (5, 5))
        self.assertEquals(q1mean[0][0], 555)
        self.assertEquals(q1mean[2][1], 666)
        vds_file.close()

        print(self.child.handled_requests.mock_calls)
        print('KinematicsSavu configure {} points took {} secs'.format(
            self.steps_to_do, datetime.now() - start_time))
        rmtree(tmp_dir)

    # def test_run(self):
    #     tmp_dir = mkdtemp() + os.path.sep
    #     self.o.configure(
    #         self.context, self.completed_steps, self.steps_to_do,
    #         generator=self.generator, fileDir=tmp_dir, formatName='odin2',
    #         fileTemplate='a_unique_name_%s_from_gda.h5')
    #     self.child.handled_requests.reset_mock()
    #     self.o.registrar = MagicMock()
    #     # run waits for this value
    #     self.child.field_registry.get_field("numCaptured").set_value(
    #         self.o.done_when_reaches)
    #     self.o.run(self.context)
    #     assert self.child.handled_requests.mock_calls == [
    #         call.when_value_matches('numCaptured', self.steps_to_do, None)]
    #     assert self.o.registrar.report.called_once
    #     assert self.o.registrar.report.call_args_list[0][0][0].steps == \
    #            self.steps_to_do
    #     rmtree(tmp_dir)
    #
    # def ________test_alternate_fails(self):
    #     # TODO: put this back in when alternates are squashed with
    #     # SquashingExcluder
    #     cols, rows, alternate = 3000, 2000, True
    #     self.steps_to_do = cols * rows
    #     xs = LineGenerator("x", "mm", 0.0, 0.5, cols, alternate=alternate)
    #     ys = LineGenerator("y", "mm", 0.0, 0.1, rows)
    #     self.generator = CompoundGenerator([ys, xs], [], [], 0.1)
    #     self.generator.prepare()
    #
    #     self.assertRaises(
    #         ValueError, self.o.configure,
    #         *(self.context, self.completed_steps, self.steps_to_do),
    #         **{'generator': self.generator,
    #            'fileDir': tmp_dir, 'formatName': 'odin3'})
    #
    # @staticmethod
    # def make_test_data():
    #     for i in range(6):
    #         value = i + 1
    #         f_num = i % 4 + 1
    #         idx = int(i / 4)
    #         name = '/data/odin123_raw_data_{:06d}.h5'.format(
    #             f_num
    #         )
    #         print('updating index {} in file {} with value {}'.format(idx, name,
    #                                                                   value))
    #         raw = h5py.File(name, 'r+', libver="latest")
    #
    #         # set values in the data
    #         print(raw.items())
    #         print(raw['data'][idx])
    #         data = np.full((1536, 2048), value, np.uint16)
    #         raw['data'][idx] = data
    #         raw.close()
    #
    # def test_excalibur_vds(self):
    #     """
    #         The HDF data for this test was created by running a 6 point scan
    #         and then using the function make_test_data above to fill each frame
    #         with its own (1 based) index
    #         """
    #     tmp_dir = mkdtemp() + os.path.sep
    #     test_data = os.path.join(os.path.dirname(
    #         os.path.realpath(__file__)), 'data/*')
    #     for f in glob.glob(test_data):
    #         copy(f, tmp_dir)
    #
    #     # Create a generator to match the test data
    #     xs = LineGenerator("x", "mm", 0.0, 4.0, 3)
    #     ys = LineGenerator("y", "mm", 0.0, 4.0, 2)
    #     compound = CompoundGenerator([ys, xs], [], [])
    #     compound.prepare()
    #
    #     # Call configure to create the VDS
    #     # This should work with relative paths but doesn't due to VDS bug
    #     self.o.configure(self.context, 0, 6, compound, formatName='odin123',
    #                      fileDir=tmp_dir, fileTemplate="%s.h5")
    #
    #     # Open the created VDS file and dataset to check values
    #     vds_path = os.path.join(tmp_dir, 'odin123.h5')
    #     vds_file = h5py.File(vds_path, "r")
    #     detector_dataset = vds_file['/entry/detector/data']
    #
    #     # Check values at indices 0,0
    #     self.assertEquals(detector_dataset[0][0][756][393], 1)
    #     self.assertEquals(detector_dataset[0][0][756][394], 1)
    #     self.assertEquals(detector_dataset[0][0][756][395], 1)
    #     self.assertEquals(detector_dataset[0][0][756][396], 1)
    #
    #     # Change first index
    #     self.assertEquals(detector_dataset[1][0][756][393], 4)
    #     self.assertEquals(detector_dataset[1][0][756][394], 4)
    #     self.assertEquals(detector_dataset[1][0][756][395], 4)
    #     self.assertEquals(detector_dataset[1][0][756][396], 4)
    #
    #     # Change second index
    #     self.assertEquals(detector_dataset[0][2][756][393], 3)
    #     self.assertEquals(detector_dataset[0][2][756][394], 3)
    #     self.assertEquals(detector_dataset[0][2][756][395], 3)
    #     self.assertEquals(detector_dataset[0][2][756][396], 3)
    #
    #     # Todo there are no gaps in my test data at present:-
    #     #  update the test data with Alans Gap fill and fix this
    #     # # Check some values near the bottom of image to ensure
    #     # # the gaps are there
    #     # assert detector_dataset[0][0][1685][1521] == 3
    #     # assert detector_dataset[1][0][1685][1521] == 131
    #     #
    #     # assert detector_dataset[0][0][1516][329] == 109
    #     # assert detector_dataset[0][1][1516][329] == 136
    #     #
    #     # # Check some values in the gaps
    #     # assert detector_dataset[0][0][395][1202] == 0
    #     # assert detector_dataset[1][0][395][1202] == 0
    #
    #     # Check detector attributes
    #     detector_group = vds_file['/entry/detector']
    #     for a, b in zip(detector_group.attrs['axes'],
    #                     ['y_set', 'x_set', '.', '.']):
    #         assert a == b
    #     assert detector_group.attrs['signal'] == 'data'
    #     assert detector_group.attrs['y_set_indices'] == 0
    #     assert detector_group.attrs['x_set_indices'] == 1
    #
    #     # Check _set datasets
    #     # N.B. units are encoded as ASCII in the original file, so come
    #     # back as type byte in Python 3
    #     stage1_x_set_dataset = vds_file['/entry/detector/x_set']
    #     assert stage1_x_set_dataset[0] == 0
    #     assert stage1_x_set_dataset[1] == 2
    #     assert str(stage1_x_set_dataset.attrs['units']) == 'mm'
    #
    #     stage1_y_set_dataset = vds_file['/entry/detector/y_set']
    #     assert stage1_y_set_dataset[0] == 0
    #     assert stage1_y_set_dataset[1] == 4
    #     assert str(stage1_y_set_dataset.attrs['units']) == 'mm'
    #
    #     vds_file.close()
    #     rmtree(tmp_dir)
