import os
import numpy as np
from datetime import datetime
from shutil import rmtree
from tempfile import mkdtemp

import h5py
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
