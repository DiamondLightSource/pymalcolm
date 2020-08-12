from xml.etree import ElementTree

from mock import call

from malcolm.core import Context, Process
from malcolm.modules.ADCore.blocks import stats_plugin_block
from malcolm.modules.ADCore.infos import FilePathTranslatorInfo
from malcolm.modules.ADCore.parts import StatsPluginPart
from malcolm.testutil import ChildTestCase


class TestStatsPluginPart(ChildTestCase):
    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            stats_plugin_block, self.process, mri="BLOCK:STAT", prefix="prefix"
        )

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_report_info(self):
        self.o = StatsPluginPart(name="m", mri="BLOCK:STAT")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()
        assert list(sorted(self.o.no_save_attribute_names)) == [
            "arrayCounter",
            "attributesFile",
            "computeStatistics",
            "enableCallbacks",
        ]
        infos = self.o.on_report_status()
        assert len(infos) == 1
        assert infos[0].name == "sum"
        assert infos[0].attr == "STATS_TOTAL"

    def test_configure(self):
        self.o = StatsPluginPart(name="m", mri="BLOCK:STAT")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()
        fileDir = "/tmp"
        part_info = {}
        infos = self.o.on_configure(self.context, part_info, fileDir)
        assert infos is None
        expected_filename = "/tmp/BLOCK_STAT-attributes.xml"
        assert self.child.handled_requests.mock_calls == [
            call.put("computeStatistics", True),
            call.put("enableCallbacks", True),
            call.put("attributesFile", expected_filename),
        ]
        expected_xml = (
            '<?xml version="1.0" ?>\n'
            "<Attributes>\n"
            '<Attribute addr="0" datatype="DOUBLE" description="Sum of the array" '
            'name="STATS_TOTAL" source="TOTAL" type="PARAM" />\n'
            "</Attributes>"
        )
        with open(expected_filename) as f:
            actual_xml = f.read().replace(">", ">\n")

        actual_tree = ElementTree.XML(actual_xml)
        expected_tree = ElementTree.XML(expected_xml)
        assert ElementTree.dump(actual_tree) == ElementTree.dump(expected_tree)

    def test_configure_windows(self):
        self.o = StatsPluginPart(name="m", mri="BLOCK:STAT", runs_on_windows=True)
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()
        fileDir = "/tmp"
        part_info = {"sth": [FilePathTranslatorInfo("X", "/tmp", "")]}
        infos = self.o.on_configure(self.context, part_info, fileDir)
        assert infos is None
        expected_filename_unix = "/tmp/BLOCK_STAT-attributes.xml"
        expected_filename_windows = "X:\\BLOCK_STAT-attributes.xml"
        assert self.child.handled_requests.mock_calls == [
            call.put("computeStatistics", True),
            call.put("enableCallbacks", True),
            call.put("attributesFile", expected_filename_windows),
        ]
        expected_xml = (
            '<?xml version="1.0" ?>\n'
            "<Attributes>\n"
            '<Attribute addr="0" datatype="DOUBLE" description="Sum of the array" '
            'name="STATS_TOTAL" source="TOTAL" type="PARAM" />\n'
            "</Attributes>"
        )
        with open(expected_filename_unix) as f:
            actual_xml = f.read().replace(">", ">\n")

        actual_tree = ElementTree.XML(actual_xml)
        expected_tree = ElementTree.XML(expected_xml)
        assert ElementTree.dump(actual_tree) == ElementTree.dump(expected_tree)
