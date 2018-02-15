from collections import OrderedDict
import unittest
from mock import MagicMock, Mock

from malcolm.core import Context
from malcolm.modules.ADCore.util import AttributeDatasetType
from malcolm.modules.ADPandABlocks.parts import PandABlocksChildPart


class PandABoxChildPartTest(unittest.TestCase):
    def setUp(self):
        self.child = OrderedDict()
        self.child["bits0Capture"] = Mock(value="no")
        self.child["bits1Capture"] = Mock(value="yes")
        self.child["encoderValue1Capture"] = Mock(value="capture")
        self.child["encoderValue1DatasetName"] = Mock(value="")
        self.child["encoderValue1DatasetType"] = Mock(value="anything")
        self.child["encoderValue2Capture"] = Mock(value="no")
        self.child["encoderValue2DatasetName"] = Mock(value="x1")
        self.child["encoderValue2DatasetType"] = Mock(value="anything")
        self.child["encoderValue3Capture"] = Mock(value="capture")
        self.child["encoderValue3DatasetName"] = Mock(value="x2")
        self.child["encoderValue3DatasetType"] = Mock(value="position")
        self.context = MagicMock(spec=Context)
        self.context.block_view.return_value = self.child
        self.o = PandABlocksChildPart(mri="P:INENC1", name="INENC1")

    def test_report_configuration(self):
        dataset_infos = self.o.report_status(self.context)
        assert len(dataset_infos) == 1
        assert dataset_infos[0].name == "x2"
        assert dataset_infos[0].type == AttributeDatasetType.POSITION
        assert dataset_infos[0].rank == 2
        assert dataset_infos[0].attr == "INENC1.ENCODER_VALUE3"

    def test_counter_configuration(self):
        self.child["encoderValue3DatasetType"] = Mock(value="monitor")
        dataset_infos = self.o.report_status(self.context)
        assert len(dataset_infos) == 1
        assert dataset_infos[0].name == "x2"
        assert dataset_infos[0].type == AttributeDatasetType.MONITOR
        assert dataset_infos[0].rank == 2
        assert dataset_infos[0].attr == "INENC1.ENCODER_VALUE3"

    def test_counter_configuration_detector(self):
        self.child["encoderValue3DatasetType"] = Mock(value="detector")
        dataset_infos = self.o.report_status(self.context)
        assert len(dataset_infos) == 1
        assert dataset_infos[0].name == "x2"
        assert dataset_infos[0].type == AttributeDatasetType.DETECTOR
        assert dataset_infos[0].rank == 2
        assert dataset_infos[0].attr == "INENC1.ENCODER_VALUE3"
