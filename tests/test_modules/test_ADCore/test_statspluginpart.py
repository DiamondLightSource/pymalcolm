from mock import call, MagicMock, ANY

from malcolm.core import Context, call_with_params, Process
from malcolm.modules.ADCore.blocks import stats_plugin_block
from malcolm.modules.ADCore.parts import StatsPluginPart
from malcolm.testutil import ChildTestCase


class TestStatsPluginPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            stats_plugin_block, self.process,
            mri="BLOCK-STAT", prefix="prefix")
        self.o = call_with_params(
            StatsPluginPart, name="m", mri="BLOCK-STAT")
        list(self.o.create_attributes())
        self.process.start()

    def test_report_info(self):
        infos = self.o.report_info(ANY)
        assert len(infos) == 1
        assert infos[0].name == "sum"
        assert infos[0].attr == "StatsTotal"

    def test_configure(self):
        completed_steps = ANY
        steps_to_do = ANY
        part_info = ANY
        params = MagicMock()
        params.filePath = "/tmp/anything.h5"
        infos = self.o.configure(
            self.context, completed_steps, steps_to_do, part_info, params)
        assert infos is None
        expected_filename = "/tmp/BLOCK-STAT-attributes.xml"
        assert self.child.handled_requests.mock_calls == [
            call.put('computeStatistics', True),
            call.put('enableCallbacks', True),
            call.put('attributesFile', expected_filename)]
        expected_xml = """<?xml version="1.0" ?>
<Attributes>
<Attribute addr="0" datatype="DOUBLE" description="Sum of the array" name="StatsTotal" source="TOTAL" type="PARAM" />
</Attributes>"""
        actual_xml = open(expected_filename).read().replace(">", ">\n")
        assert actual_xml.splitlines() == expected_xml.splitlines()

