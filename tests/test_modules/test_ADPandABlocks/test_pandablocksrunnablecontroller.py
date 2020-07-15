import unittest
from collections import OrderedDict

from annotypes import add_call_types
from mock import patch
from scanpointgenerator import CompoundGenerator, StaticPointGenerator

from malcolm.core import Part, Process
from malcolm.modules.ADPandABlocks.controllers import PandARunnableController
from malcolm.modules.ADPandABlocks.util import DatasetPositionsTable
from malcolm.modules.builtin.util import LayoutTable
from malcolm.modules.pandablocks.pandablocksclient import BlockData, FieldData
from malcolm.modules.scanning.hooks import APartInfo, ConfigureHook
from malcolm.modules.scanning.infos import DatasetType
from malcolm.modules.scanning.parts import DatasetTablePart


class DSGather(Part):
    part_info = None

    def setup(self, registrar):
        self.register_hooked(ConfigureHook, self.configure)

    @add_call_types
    def configure(self, part_info: APartInfo) -> None:
        self.part_info = part_info


class PandABlocksRunnableControllerTest(unittest.TestCase):
    @patch("malcolm.modules.ADCore.includes.adbase_parts")
    @patch(
        "malcolm.modules.pandablocks.controllers."
        "pandamanagercontroller.PandABlocksClient"
    )
    def setUp(self, mock_client, mock_adbase_parts):
        mock_adbase_parts.return_value = ([], [])
        self.process = Process()
        self.o = PandARunnableController(mri="P", config_dir="/tmp", prefix="PV:")
        self.o.add_part(DatasetTablePart("DSET"))
        self.client = self.o._client
        self.client.started = False
        blocks_data = OrderedDict()
        fields = OrderedDict()
        fields["TS"] = FieldData("ext_out", "", "Timestamp", ["No", "Capture"])
        blocks_data["PCAP"] = BlockData(1, "", fields)
        fields = OrderedDict()
        fields["VAL"] = FieldData("pos_out", "", "Output", ["No", "Capture"])
        blocks_data["INENC"] = BlockData(4, "", fields)
        self.client.get_blocks_data.return_value = blocks_data
        self.process.add_controller(self.o)
        self.process.start()

    def tearDown(self):
        self.process.stop()

    def test_initial_changes(self):
        pcap = self.process.block_view("P:PCAP")
        inenc = self.process.block_view("P:INENC1")
        with self.assertRaises(Exception):
            pcap.ts
        assert pcap.tsCapture.value == "No"
        assert inenc.val.value == 0.0
        with self.assertRaises(Exception):
            inenc.valCapture

    def test_pcap_visible(self):
        t = LayoutTable.from_rows([["PCAP", "", 0, 0, True]])
        block = self.process.block_view("P")
        assert "attributesToCapture" not in block
        block.layout.put_value(t)
        assert block.attributesToCapture.meta.tags == ["widget:table"]

    def test_report_configuration(self):
        p = DSGather("DS")
        self.o.add_part(p)
        b = self.process.block_view("P")
        pos_table = DatasetPositionsTable(
            name=["INENC1.VAL", "INENC2.VAL", "INENC3.VAL", "INENC4.VAL"],
            value=[0] * 4,
            offset=[0] * 4,
            scale=[0] * 4,
            units=[""] * 4,
            capture=["Diff", "No", "Min Max Mean", "Diff"],
            datasetName=["", "x1", "x2", "x3"],
            datasetType=["monitor", "monitor", "position", "monitor"],
        )
        b.positions.put_value(pos_table)
        b.configure(generator=CompoundGenerator([StaticPointGenerator(1)], [], []))
        dataset_infos = p.part_info["busses"]
        assert len(dataset_infos) == 4
        assert dataset_infos[0].name == "x2.min"
        assert dataset_infos[0].type == DatasetType.POSITION_MIN
        assert dataset_infos[0].attr == "INENC3.VAL.Min"
        assert dataset_infos[1].name == "x2.max"
        assert dataset_infos[1].type == DatasetType.POSITION_MAX
        assert dataset_infos[1].attr == "INENC3.VAL.Max"
        assert dataset_infos[2].name == "x2.value"
        assert dataset_infos[2].type == DatasetType.POSITION_VALUE
        assert dataset_infos[2].attr == "INENC3.VAL.Mean"
        assert dataset_infos[3].name == "x3.data"
        assert dataset_infos[3].type == DatasetType.MONITOR
        assert dataset_infos[3].attr == "INENC4.VAL.Diff"
