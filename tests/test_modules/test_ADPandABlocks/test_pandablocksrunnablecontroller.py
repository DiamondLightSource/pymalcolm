from collections import OrderedDict
import unittest
from mock import call, Mock, patch, ANY

from malcolm.modules.ADPandABlocks.controllers import \
    PandABlocksRunnableController
from malcolm.modules.pandablocks.pandablocksclient import \
    FieldData, BlockData


class PandABlocksRunnableControllerTest(unittest.TestCase):
    @patch("cothread.catools")
    @patch("malcolm.modules.pandablocks.controllers."
           "pandablocksmanagercontroller.PandABlocksClient")
    def setUp(self, mock_client, catools):
        self.process = Mock()
        self.o = PandABlocksRunnableController(
            mri="P", config_dir="/tmp", prefix="PV:")
        self.o.setup(self.process)
        blocks_data = OrderedDict()
        fields = OrderedDict()
        fields["TS"] = FieldData("ext_out", "", "Timestamp", ["No", "Capture"])
        blocks_data["PCAP"] = BlockData(1, "", fields)
        fields = OrderedDict()
        fields["VAL"] = FieldData("pos_out", "", "Output", ["No", "Capture"])
        blocks_data["INENC"] = BlockData(1, "", fields)
        self.client = self.o.client
        self.client.get_blocks_data.return_value = blocks_data
        self.o._make_blocks_parts()

    def _blocks(self):
        pcap = self.process.add_controller.call_args_list[0][0][0]
        assert pcap.mri == "P:PCAP"
        pcap.setup(self.process)
        inenc = self.process.add_controller.call_args_list[1][0][0]
        assert inenc.mri == "P:INENC"
        inenc.setup(self.process)
        return pcap.make_view(), inenc.make_view()

    def test_initial_changes(self):
        assert self.process.mock_calls == [
            call.add_controller(ANY, timeout=5),
            call.add_controller(ANY, timeout=5)]
        pcap, inenc = self._blocks()
        with self.assertRaises(Exception):
            pcap.ts
        assert pcap.tsCapture.value == "No"
        assert pcap.tsDatasetName.value == ""
        assert pcap.tsDatasetType.value.value == "monitor"
        assert inenc.val.value == 0.0
        assert inenc.valCapture.value == "No"
        assert inenc.valDatasetName.value == ""
        assert inenc.valDatasetType.value.value == "position"
