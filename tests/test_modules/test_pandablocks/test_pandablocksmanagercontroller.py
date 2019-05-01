from collections import OrderedDict
import unittest
from mock import patch, ANY

from malcolm.core import Process, Queue, Subscribe
from malcolm.modules.pandablocks.controllers import PandAManagerController
from malcolm.modules.pandablocks.pandablocksclient import \
    FieldData, BlockData


class PandABlocksManagerControllerTest(unittest.TestCase):
    @patch("malcolm.modules.pandablocks.controllers.pandamanagercontroller.PandABlocksClient")
    def setUp(self, mock_client):
        self.process = Process()
        self.o = PandAManagerController(
            mri="P", config_dir="/tmp", poll_period=1000)
        self.client = self.o._client
        self.client.started = False
        blocks_data = OrderedDict()
        fields = OrderedDict()
        fields["INP"] = FieldData("pos_mux", "", "Input A", ["ZERO", "COUNTER.OUT"])
        fields["START"] = FieldData("param", "", "Start position", [])
        fields["STEP"] = FieldData("param", "", "Step position", [])
        fields["OUT"] = FieldData("bit_out", "", "Output", [])
        blocks_data["PCOMP"] = BlockData(1, "", fields)
        fields = OrderedDict()
        fields["INP"] = FieldData("bit_mux", "", "Input", ["ZERO", "TTLIN.VAL"])
        fields["START"] = FieldData("param", "pos", "Start position", [])
        fields["OUT"] = FieldData("pos_out", "", "Output", ["No", "Capture"])
        blocks_data["COUNTER"] = BlockData(1, "", fields)
        fields = OrderedDict()
        fields["VAL"] = FieldData("bit_out", "", "Output", [])
        blocks_data["TTLIN"] = BlockData(2, "", fields)
        self.client.get_blocks_data.return_value = blocks_data
        changes = [
            ["PCOMP.INP", "ZERO"],
            ["PCOMP.STEP", "0"],
            ["PCOMP.START", "0"],
            ["PCOMP.OUT", "0"],
            ["COUNTER.INP", "ZERO"],
            ["COUNTER.INP.DELAY", "0"],
            ["COUNTER.OUT", "0"],
            ["COUNTER.OUT.SCALE", "1"],
            ["COUNTER.OUT.OFFSET", "0"],
            ["COUNTER.OUT.UNITS", ""],
            ["TTLIN1.VAL", "0"],
            ["TTLIN2.VAL", "0"],
        ]
        self.client.get_changes.return_value = changes
        pcap_bit_fields = {
            "PCAP.BITS0.CAPTURE": ["TTLIN1.VAL", "TTLIN2.VAL", "PCOMP.OUT", ""]
        }
        self.client.get_pcap_bits_fields.return_value = pcap_bit_fields
        self.process.add_controller(self.o)
        self.process.start()

    def tearDown(self):
        self.process.stop()

    def test_initial_changes(self):
        assert self.process.mri_list == [
            'P', 'P:PCOMP', 'P:COUNTER', 'P:TTLIN1', 'P:TTLIN2']
        assert self.o._bit_outs == {
            'TTLIN1.VAL': False, 'TTLIN2.VAL': False, 'PCOMP.OUT': False}
        pcomp = self.process.block_view('P:PCOMP')
        counter = self.process.block_view('P:COUNTER')
        ttlin = self.process.block_view('P:TTLIN1')
        assert pcomp.inp.value == "ZERO"
        assert pcomp.start.value == 0.0
        assert pcomp.step.value == 0.0
        assert pcomp.out.value is False
        assert counter.inp.value == "ZERO"
        assert counter.inpDelay.value == 0
        assert counter.out.value == 0.0
        assert ttlin.val.value is False

    def test_toggling_bit_outs(self):
        ttlin = self.process.block_view('P:TTLIN1')
        assert ttlin.val.value is False

        # Change to a different value, should change once and stick
        self.o.handle_changes([("TTLIN1.VAL", "1")])
        assert ttlin.val.value is True
        self.o.handle_changes(())
        assert ttlin.val.value is True
        self.o.handle_changes(())
        assert ttlin.val.value is True

        # Change to same value, should toggle once
        self.o.handle_changes([("TTLIN1.VAL", "1")])
        assert ttlin.val.value is False
        self.o.handle_changes(())
        assert ttlin.val.value is True
        self.o.handle_changes(())
        assert ttlin.val.value is True

        # Change back, should change once and stick
        self.o.handle_changes([("TTLIN1.VAL", "0")])
        assert ttlin.val.value is False
        self.o.handle_changes(())
        assert ttlin.val.value is False
        self.o.handle_changes(())
        assert ttlin.val.value is False

        # Change to same value, should toggle once
        self.o.handle_changes([("TTLIN1.VAL", "0")])
        assert ttlin.val.value is True
        self.o.handle_changes(())
        assert ttlin.val.value is False
        self.o.handle_changes(())
        assert ttlin.val.value is False

        # Change to same value, then get the opposite next tick
        self.o.handle_changes([("TTLIN1.VAL", "0")])
        assert ttlin.val.value is True
        self.o.handle_changes([("TTLIN1.VAL", "1")])
        assert ttlin.val.value is False
        self.o.handle_changes(())
        assert ttlin.val.value is True
        self.o.handle_changes(())
        assert ttlin.val.value is True

    def test_constant_toggling_bit_outs(self):
        ttlin = self.process.block_view('P:TTLIN1')
        assert ttlin.val.value is False

        # Constant updates, should toggle each time
        self.o.handle_changes([("TTLIN1.VAL", "0")])
        assert ttlin.val.value is True
        self.o.handle_changes([("TTLIN1.VAL", "1")])
        assert ttlin.val.value is False
        self.o.handle_changes([("TTLIN1.VAL", "1")])
        assert ttlin.val.value is True
        self.o.handle_changes([("TTLIN1.VAL", "1")])
        assert ttlin.val.value is False
        self.o.handle_changes([("TTLIN1.VAL", "1")])
        assert ttlin.val.value is True
        self.o.handle_changes([("TTLIN1.VAL", "0")])
        assert ttlin.val.value is False
        self.o.handle_changes([("TTLIN1.VAL", "0")])
        assert ttlin.val.value is True
        self.o.handle_changes([("TTLIN1.VAL", "1")])
        assert ttlin.val.value is False
        self.o.handle_changes([("TTLIN1.VAL", "0")])
        assert ttlin.val.value is True
        self.o.handle_changes(())
        assert ttlin.val.value is False
        self.o.handle_changes(())
        assert ttlin.val.value is False

    def test_table_deltas(self):
        queue = Queue()
        subscribe = Subscribe(path=["P"], delta=True)
        subscribe.set_callback(queue.put)
        self.o.handle_request(subscribe)
        delta = queue.get()
        table = delta.changes[0][1]["bits"]["value"]
        assert table.name == ['TTLIN1.VAL', 'TTLIN2.VAL', 'PCOMP.OUT']
        assert table.value == [False, False, False]
        assert table.capture == [False, False, False]

        self.o.handle_changes([("TTLIN1.VAL", "1")])
        delta = queue.get()
        assert delta.changes == [
            [['bits', 'value', 'value'], [True, False, False]],
            [['bits', 'timeStamp'], ANY]
        ]

