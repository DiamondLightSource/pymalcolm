import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import call, MagicMock, ANY

from malcolm.core import Context, call_with_params
from malcolm.modules.ADCore.parts import StatsPluginPart


class TestStatsPluginPart(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock(spec=Context)
        self.o = call_with_params(
            StatsPluginPart, name="stat", mri="BLOCK-STAT")

    def test_report_info(self):
        infos = self.o.report_info(ANY)
        self.assertEqual(len(infos), 1)
        self.assertEqual(infos[0].name, "sum")
        self.assertEqual(infos[0].attr, "StatsTotal")

    def test_configure(self):
        completed_steps = ANY
        steps_to_do = ANY
        part_info = ANY
        params = MagicMock()
        params.filePath = "/tmp/anything.h5"
        infos = self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)
        self.assertIsNone(infos)
        expected_filename = "/tmp/BLOCK-STAT-attributes.xml"
        assert self.context.mock_calls == [
            call.block_view('BLOCK-STAT'),
            call.block_view().put_attribute_values_async(dict(
                enableCallbacks=True,
                computeStatistics=True)),
            call.block_view().attributesFile.put_value(expected_filename),
            call.wait_all_futures(ANY)]
        expected_xml = """<?xml version="1.0" ?>
<Attributes>
<Attribute addr="0" datatype="DOUBLE" description="Sum of the array" name="StatsTotal" source="TOTAL" type="PARAM" />
</Attributes>"""
        actual_xml = open(expected_filename).read().replace(">", ">\n")
        self.assertEqual(actual_xml.splitlines(), expected_xml.splitlines())

if __name__ == "__main__":
    unittest.main(verbosity=2)
