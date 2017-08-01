from collections import OrderedDict
import unittest
from mock import call, Mock, patch, ANY, MagicMock
from xml.etree import cElementTree as ET

from malcolm.core import call_with_params
from malcolm.modules.pandablocks.controllers import PandABlocksManagerController
from malcolm.modules.pandablocks.controllers.pandablocksclient import \
    FieldData, BlockData


class PandABlocksManagerControllerTest(unittest.TestCase):
    @patch("malcolm.modules.pandablocks.controllers.pandablocksmanagercontroller.PandABlocksClient")
    def setUp(self, mock_client):
        self.process = Mock()
        self.o = call_with_params(
            PandABlocksManagerController, self.process, [], mri="P", configDir="/tmp")
        blocks_data = OrderedDict()
        fields = OrderedDict()
        fields["INP"] = FieldData("pos_mux", "", "Input A", ["ZERO", "COUNTER.OUT"])
        fields["START"] = FieldData("param", "pos", "Start position", [])
        fields["STEP"] = FieldData("param", "relative_pos", "Step position", [])
        fields["OUT"] = FieldData("bit_out", "", "Output", [])
        blocks_data["PCOMP"] = BlockData(1, "", fields)
        fields = OrderedDict()
        fields["INP"] = FieldData("bit_mux", "", "Input", ["ZERO", "TTLIN.VAL"])
        fields["START"] = FieldData("param", "pos", "Start position", [])
        fields["OUT"] = FieldData("pos_out", "", "Output", ["No", "Capture"])
        blocks_data["COUNTER"] = BlockData(1, "", fields)
        fields = OrderedDict()
        fields["VAL"] = FieldData("bit_out", "", "Output", [])
        blocks_data["TTLIN"] = BlockData(1, "", fields)
        self.client = self.o.client
        self.client.get_blocks_data.return_value = blocks_data
        self.o._make_blocks_parts()
        changes = OrderedDict()
        changes["PCOMP.INP"] = "ZERO"
        for field_name in ("START", "STEP"):
            changes["PCOMP.%s" % field_name] = "0"
            changes["PCOMP.%s.SCALE" % field_name] = "1"
            changes["PCOMP.%s.OFFSET" % field_name] = "0"
            changes["PCOMP.%s.UNITS" % field_name] = ""
        changes["PCOMP.OUT"] = "0"
        changes["COUNTER.INP"] = "ZERO"
        changes["COUNTER.INP.DELAY"] = "0"
        changes["COUNTER.OUT"] = "0"
        changes["COUNTER.OUT.SCALE"] = "1"
        changes["COUNTER.OUT.OFFSET"] = "0"
        changes["COUNTER.OUT.UNITS"] = ""
        changes["TTLIN.VAL"] = "0"
        self.o.handle_changes(changes)
        # Once more to let the bit_outs toggle back
        self.o.handle_changes({})

    def _blocks(self):
        pcomp = self.process.add_controller.call_args_list[0][0][1].block_view()
        counter = self.process.add_controller.call_args_list[1][0][
            1].block_view()
        ttlin = self.process.add_controller.call_args_list[2][0][1].block_view()
        return pcomp, counter, ttlin

    def test_initial_changes(self):
        assert self.process.mock_calls == [
            call.add_controller('P:PCOMP', ANY),
            call.add_controller('P:COUNTER', ANY),
            call.add_controller('P:TTLIN', ANY)]
        pcomp, counter, ttlin = self._blocks()
        assert pcomp.inp.value == "ZERO"
        assert pcomp.inpCurrent.value == 0.0
        assert pcomp.start.value == 0.0
        assert pcomp.step.value == 0.0
        assert pcomp.out.value is False
        assert counter.inp.value == "ZERO"
        assert counter.inpDelay.value == 0
        assert counter.inpCurrent.value is False
        assert counter.out.value == 0.0
        assert counter.outScale.value == 1.0
        assert counter.outOffset.value == 0.0
        assert counter.outUnits.value == ""
        assert ttlin.val.value is False

    def test_rewiring(self):
        pcomp, counter, ttlin = self._blocks()
        self.o.handle_changes({"COUNTER.OUT": 32.0})
        assert counter.out.value== 32.0
        self.o.handle_changes({"PCOMP.INP": "COUNTER.OUT"})
        assert pcomp.inp.value == "COUNTER.OUT"
        assert pcomp.inpCurrent.value == 32.0
        self.o.handle_changes({"PCOMP.INP": "ZERO"})
        assert pcomp.inp.value == "ZERO"
        assert pcomp.inpCurrent.value == 0.0

    def test_scale_offset_following(self):
        pcomp, counter, ttlin = self._blocks()
        assert self.client.send.call_args_list == [
            call('PCOMP.START.SCALE=1\n'),
            call('PCOMP.START.OFFSET=0\n'),
            call('PCOMP.START.UNITS=\n'),
            call('PCOMP.STEP.SCALE=1\n'),
            call('PCOMP.STEP.UNITS=\n'),
            call('COUNTER.START.SCALE=1\n'),
            call('COUNTER.START.OFFSET=0\n'),
            call('COUNTER.START.UNITS=\n'),
        ]
        self.client.send.reset_mock()
        self.o.handle_changes({"PCOMP.INP": "COUNTER.OUT"})
        assert pcomp.inp.value == "COUNTER.OUT"
        assert pcomp.inpCurrent.value == 0.0
        assert self.client.send.call_args_list == [
            call('PCOMP.START.SCALE=1.0\n'),
            call('PCOMP.START.OFFSET=0.0\n'),
            call('PCOMP.START.UNITS=\n'),
            call('PCOMP.STEP.SCALE=1.0\n'),
            call('PCOMP.STEP.UNITS=\n')
        ]
        self.client.send.reset_mock()
        self.o.handle_changes({"COUNTER.OUT.OFFSET": "5.2"})
        assert self.client.send.call_args_list == [
            call('COUNTER.START.OFFSET=5.2\n'),
            call('PCOMP.START.OFFSET=5.2\n')
        ]
        self.client.send.reset_mock()
        self.o.handle_changes({"COUNTER.OUT.SCALE": "0.2"})
        assert self.client.send.call_args_list == [
            call('COUNTER.START.SCALE=0.2\n'),
            call('PCOMP.START.SCALE=0.2\n'),
            call('PCOMP.STEP.SCALE=0.2\n'),
        ]
        self.client.send.reset_mock()
        self.o.handle_changes({"PCOMP.INP": "ZERO"})
        assert self.client.send.call_args_list == [
            call('PCOMP.START.SCALE=1\n'),
            call('PCOMP.START.OFFSET=0\n'),
            call('PCOMP.START.UNITS=\n'),
            call('PCOMP.STEP.SCALE=1\n'),
            call('PCOMP.STEP.UNITS=\n')
        ]

    def test_lut(self):
        # LUT symbol
        assert self.o._get_lut_icon_elements(0) == {
            'AND', 'NOT', 'OR', 'notA', 'notB', 'notC', 'notD', 'notE'}
        # A&B&C&D&E
        assert self.o._get_lut_icon_elements(0x80000000) == {
            'LUT', 'NOT', 'OR', 'notA', 'notB', 'notC', 'notD', 'notE'}
        # !A&!B&!C&!D&!E
        assert self.o._get_lut_icon_elements(0x1) == {
            'LUT', 'NOT', 'OR'}
        # A&!B
        assert self.o._get_lut_icon_elements(0xff0000) == {
            'C', 'D', 'E', 'LUT', 'NOT', 'OR', 'notA', 'notC', 'notD', 'notE'}
        # A&C should be LUT
        assert self.o._get_lut_icon_elements(0xf0f00000) == {
             'AND', 'NOT', 'OR', 'notA', 'notB', 'notC', 'notD', 'notE'}
        # !C
        assert self.o._get_lut_icon_elements(0xf0f0f0f) == {
            'A', 'AND', 'B', 'D', 'E', 'LUT', 'OR', 'notA', 'notB', 'notC', 'notD', 'notE'}\
        # A|B
        assert self.o._get_lut_icon_elements(0xffffff00) == {
            'AND', 'C', 'D', 'E', 'LUT', 'NOT', 'notA', 'notB', 'notC', 'notD', 'notE'}

    def test_symbol(self):
        m = MagicMock()
        self.o._blocks_parts["LUT1"] = dict(icon=m)
        # !A&!B&!C&!D&!E
        self.client.get_field.return_value = "1"
        self.o._set_lut_icon("LUT1")
        svg_text = m.attr.set_value.call_args[0][0]
        root = ET.fromstring(svg_text)
        assert len(root.findall(".//*[@id='A']")) == 1
        assert len(root.findall(".//*[@id='notA']")) == 1
        assert len(root.findall(".//*[@id='OR']")) == 0
        assert len(root.findall(".//*[@id='AND']")) == 1
