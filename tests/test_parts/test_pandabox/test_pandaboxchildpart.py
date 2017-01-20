import os
import sys
from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import call, MagicMock, Mock

from malcolm.core import Table
from malcolm.core.vmetas import TableMeta, BooleanArrayMeta, NumberArrayMeta
from malcolm.parts.pandabox.pandaboxchildpart import PandABoxChildPart


class PandABoxChildPartTest(unittest.TestCase):
    def setUp(self):
        self.process = MagicMock()
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

        self.params = MagicMock(mri="P:INENC1")
        self.params.name="INENC1"
        self.process.get_block.return_value = self.child
        self.o = PandABoxChildPart(self.process, self.params)
        list(self.o.create_attributes())

    def test_init(self):
        self.assertEqual(self.o.child, self.child)

    def test_report_configuration(self):
        dataset_infos = self.o.report_configuration(None)
        self.assertEqual(len(dataset_infos), 1)
        self.assertEqual(dataset_infos[0].name, "x2")
        self.assertEqual(dataset_infos[0].type, "position")
        self.assertEqual(dataset_infos[0].rank, 2)
        self.assertEqual(dataset_infos[0].attr, "INENC1.ENCODER_VALUE3")

    def test_counter_configuration(self):
        self.child["encoderValue3DatasetType"] = Mock(value="monitor")
        dataset_infos = self.o.report_configuration(None)
        self.assertEqual(len(dataset_infos), 1)
        self.assertEqual(dataset_infos[0].name, "x2")
        self.assertEqual(dataset_infos[0].type, "monitor")
        self.assertEqual(dataset_infos[0].rank, 2)
        self.assertEqual(dataset_infos[0].attr, "INENC1.ENCODER_VALUE3")

    def test_counter_configuration_detector(self):
        self.child["encoderValue3DatasetType"] = Mock(value="detector")
        dataset_infos = self.o.report_configuration(None)
        self.assertEqual(len(dataset_infos), 1)
        self.assertEqual(dataset_infos[0].name, "x2")
        self.assertEqual(dataset_infos[0].type, "detector")
        self.assertEqual(dataset_infos[0].rank, 2)
        self.assertEqual(dataset_infos[0].attr, "INENC1.ENCODER_VALUE3")

if __name__ == "__main__":
    unittest.main(verbosity=2)
