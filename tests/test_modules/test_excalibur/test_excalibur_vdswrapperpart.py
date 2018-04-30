import unittest
import h5py
import os

from scanpointgenerator import LineGenerator, CompoundGenerator

from malcolm.modules.excalibur.parts import VDSWrapperPart


class TestExcaliburVDSWrapperPart(unittest.TestCase):

    EXCALIBUR_FILE_PATH = \
        os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data'), 'test-EXCALIBUR.h5')

    def setUp(self):
        self.o = VDSWrapperPart("Excalibur_Test", "int32", 259, 2069)

    def tearDown(self):
        if os.path.exists(self.EXCALIBUR_FILE_PATH):
            os.remove(self.EXCALIBUR_FILE_PATH)

    def test_init(self):
        assert self.o.name == "Excalibur_Test"
        assert self.o.data_type == "int32"
        assert self.o.stripe_height == 259
        assert self.o.stripe_width == 2069

    def test_configure(self):
        # Create a generator to match the test data
        line1 = LineGenerator('stage1_y', 'mm', -0.755, -0.754, 2)
        line2 = LineGenerator('stage1_x', 'mm', 11.45, 11.451, 2)
        compound = CompoundGenerator([line1, line2], [], [])
        compound.prepare()

        file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')

        # Call configure to create the VDS
        # TODO This should work with relative paths but doesn't due to VDS bug
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

        # Check some values near the bottom of image to ensure the gaps are there
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
        # N.B. units are encoded as ASCII in the original file, so come back as type byte in Python 3
        stage1_x_set_dataset = vds_file['/entry/detector/stage1_x_set']
        assert stage1_x_set_dataset[0] == 11.45
        assert stage1_x_set_dataset[1] == 11.451
        assert stage1_x_set_dataset.attrs['units'] == b'mm'

        stage1_y_set_dataset = vds_file['/entry/detector/stage1_y_set']
        assert stage1_y_set_dataset[0] == -0.755
        assert stage1_y_set_dataset[1] == -0.754
        assert stage1_y_set_dataset.attrs['units'] == b'mm'

        vds_file.close()
