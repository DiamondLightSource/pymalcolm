import os
import sys
from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from mock import call, Mock, patch, ANY

from malcolm.core import call_with_params
from malcolm.modules.ADPandABlocks.controllers import PandABlocksRunnableController
from malcolm.modules.pandablocks.controllers.pandablocksclient import \
    FieldData, BlockData


class PandABlocksManagerControllerTest(unittest.TestCase):
    @patch("malcolm.modules.pandablocks.controllers.pandablocksmanagercontroller.PandABlocksClient")
    def setUp(self, mock_client):
        self.process = Mock()
        self.o = call_with_params(
            PandABlocksRunnableController, self.process, [], mri="P",
            configDir="/tmp", areaDetectorPrefix="PV:")
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
        pcap = self.process.add_controller.call_args_list[0][0][1].block_view()
        inenc = self.process.add_controller.call_args_list[1][0][1].block_view()
        return pcap, inenc

    def test_initial_changes(self):
        assert self.process.mock_calls == [
            call.add_controller('P:PCAP', ANY),
            call.add_controller('P:INENC', ANY)]
        pcap, inenc = self._blocks()
        assert not hasattr(pcap, "ts")
        assert pcap.tsCapture.value == "No"
        assert pcap.tsDatasetName.value == ""
        assert pcap.tsDatasetType.value == "monitor"
        assert inenc.val.value == 0.0
        assert inenc.valCapture.value == "No"
        assert inenc.valDatasetName.value == ""
        assert inenc.valDatasetType.value == "position"


if __name__ == "__main__":
    unittest.main(verbosity=2)
