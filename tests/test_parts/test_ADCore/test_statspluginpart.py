import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, ANY

from malcolm.parts.ADCore.statspluginpart import StatsPluginPart


class TestStatsPluginPart(unittest.TestCase):

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()

        def getitem(name):
            return name

        self.child.__getitem__.side_effect = getitem

        self.params = MagicMock()
        self.params.mri = "BLOCK-STAT"
        self.process.get_block.return_value = self.child
        self.o = StatsPluginPart(self.process, self.params)

    def test_report_info(self):
        infos = self.o.report_info(ANY)
        self.assertEqual(len(infos), 1)
        self.assertEqual(infos[0].name, "sum")
        self.assertEqual(infos[0].attr, "StatsTotal")

    def test_configure(self):
        task = MagicMock()
        completed_steps = ANY
        steps_to_do = ANY
        part_info = ANY
        params = MagicMock()
        params.filePath = "/tmp/anything.h5"
        infos = self.o.configure(
            task, completed_steps, steps_to_do, part_info, params)
        self.assertIsNone(infos)
        task.put_many_async.assert_called_once_with(self.child, dict(
            enableCallbacks=True,
            computeStatistics=True))
        expected_filename = "/tmp/BLOCK-STAT-attributes.xml"
        task.put_async.assert_called_once_with(
            self.child["attributesFile"], expected_filename)
        expected_xml = """<?xml version="1.0" ?>
<Attributes>
<Attribute addr="0" datatype="DOUBLE" description="Sum of the array" name="StatsTotal" source="TOTAL" type="PARAM" />
</Attributes>"""
        actual_xml = open(expected_filename).read().replace(">", ">\n")
        self.assertEqual(actual_xml.splitlines(), expected_xml.splitlines())

if __name__ == "__main__":
    unittest.main(verbosity=2)
