from mock import call, MagicMock, ANY

from malcolm.core import Context, Process
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
        self.o = StatsPluginPart(name="m", mri="BLOCK-STAT")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_report_info(self):
        infos = self.o.report_status()
        assert len(infos) == 1
        assert infos[0].name == "sum"
        assert infos[0].attr == "STATS_TOTAL"

    def test_configure(self):
        fileDir = "/tmp"
        infos = self.o.configure(self.context, fileDir)
        assert infos is None
        expected_filename = "/tmp/BLOCK-STAT-attributes.xml"
        assert self.child.handled_requests.mock_calls == [
            call.put('computeStatistics', True),
            call.put('enableCallbacks', True),
            call.put('attributesFile', expected_filename)]
        expected_xml = """<?xml version="1.0" ?>
<Attributes>
<Attribute addr="0" datatype="DOUBLE" description="Sum of the array" name="STATS_TOTAL" source="TOTAL" type="PARAM" />
</Attributes>"""
        with open(expected_filename) as f:
            actual_xml = f.read().replace(">", ">\n")
        assert actual_xml.splitlines() == expected_xml.splitlines()

