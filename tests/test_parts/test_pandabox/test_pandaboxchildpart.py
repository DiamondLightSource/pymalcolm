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
        self.child["encoderValue2Capture"] = Mock(value="no")
        self.child["encoderValue2DatasetName"] = Mock(value="x1.value")
        self.child["encoderValue3Capture"] = Mock(value="capture")
        self.child["encoderValue3DatasetName"] = Mock(value="x2.value")
        self.child["counterCapture"] = Mock(value="capture")
        self.child["counterDatasetName"] = Mock(value="izero")

        self.params = MagicMock()
        self.process.get_block.return_value = self.child
        self.o = PandABoxChildPart(self.process, self.params)
        list(self.o.create_attributes())

    def test_init(self):
        self.assertEqual(self.o.child, self.child)

    def test_report_configuration(self):
        dataset_infos = self.o.report_configuration(None)
        self.assertEqual(len(dataset_infos), 2)
        self.assertEqual(dataset_infos[0].name, "x2.value")
        self.assertEqual(dataset_infos[0].type, "positioner")
        self.assertEqual(dataset_infos[0].rank, 0)
        self.assertEqual(dataset_infos[0].attr, "ENCODER_VALUE3")
        self.assertEqual(dataset_infos[1].name, "izero")
        self.assertEqual(dataset_infos[1].type, "monitor")
        self.assertEqual(dataset_infos[1].rank, 0)
        self.assertEqual(dataset_infos[1].attr, "COUNTER")

if __name__ == "__main__":
    unittest.main(verbosity=2)
