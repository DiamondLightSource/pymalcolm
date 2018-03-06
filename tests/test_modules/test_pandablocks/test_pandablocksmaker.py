from collections import OrderedDict
import unittest
from mock import Mock

from malcolm.core import BooleanMeta, ChoiceMeta, NumberMeta, StringMeta
from malcolm.modules.pandablocks.pandablocksclient import \
    BlockData, FieldData
from malcolm.modules.pandablocks.parts.pandablocksmaker import PandABlocksMaker


class PandABoxBlockMakerTest(unittest.TestCase):
    def setUp(self):
        self.client = Mock()

    def test_block_fields_adder(self):
        fields = OrderedDict()
        block_data = BlockData(2, "Adder description", fields)
        fields["INPA"] = FieldData("pos_mux", "", "Input A", ["A.OUT", "B.OUT"])
        fields["INPB"] = FieldData("pos_mux", "", "Input B", ["A.OUT", "B.OUT"])
        fields["DIVIDE"] = FieldData("param", "enum", "Divide output",
                                     ["/1", "/2", "/4"])
        fields["OUT"] = FieldData("pos_out", "", "Output", ["No", "Capture"])
        o = PandABlocksMaker(self.client, "ADDER1", block_data)
        assert list(o.parts) == [
            'icon',
            'label',
            'inputs',
            'INPA',
            'INPA.CURRENT',
            'INPB',
            'INPB.CURRENT',
            'parameters',
            'DIVIDE',
            'outputs',
            'OUT',
            'OUT.UNITS',
            'OUT.SCALE',
            'OUT.OFFSET',
            'OUT.SCALED',
            'OUT.CAPTURE',
            'OUT.DATA_DELAY']

        group = o.parts["inputs"]
        assert group.name == "inputs"
        assert group.attr.meta.tags == ["widget:group", "config:1"]

        inpa = o.parts["INPA"]
        assert inpa.block_name == "ADDER1"
        assert inpa.field_name == "INPA"
        assert inpa.meta.writeable == True
        self.assertIsInstance(inpa.meta, ChoiceMeta)
        assert inpa.meta.tags == [
            "group:inputs", "inport:int32:ZERO", "widget:combo", "config:1"]
        assert inpa.meta.choices == ["A.OUT", "B.OUT"]

        val = o.parts["INPA.CURRENT"]
        assert val.block_name == "ADDER1"
        assert val.meta.writeable == False
        self.assertIsInstance(val.meta, NumberMeta)
        assert val.meta.dtype == "int32"
        assert val.meta.tags == [
            "group:inputs", "widget:textupdate"]

        valb = o.parts["INPB"]
        assert valb.field_name == "INPB"

        divide = o.parts["DIVIDE"]
        assert divide.block_name == "ADDER1"
        assert divide.field_name == "DIVIDE"
        assert divide.meta.writeable == True
        self.assertIsInstance(divide.meta, ChoiceMeta)
        assert divide.meta.tags == [
            "group:parameters", "widget:combo", "config:1"]
        assert divide.meta.choices == ["/1", "/2", "/4"]

        out = o.parts["OUT"]
        assert out.block_name == "ADDER1"
        assert out.field_name == "OUT"
        assert out.meta.writeable == False
        self.assertIsInstance(out.meta, NumberMeta)
        assert out.meta.dtype == "int32"
        assert out.meta.tags == [
            "group:outputs", "outport:int32:ADDER1.OUT",
            "widget:textupdate"]

        units = o.parts["OUT.UNITS"]
        assert units.block_name == "ADDER1"
        assert units.field_name == "OUT.UNITS"
        assert units.meta.writeable == True
        self.assertIsInstance(units.meta, StringMeta)
        assert units.meta.tags == [
            "group:outputs", "widget:textinput", "config:1"]

        scale = o.parts["OUT.SCALE"]
        assert scale.block_name == "ADDER1"
        assert scale.field_name == "OUT.SCALE"
        assert scale.meta.writeable == True
        self.assertIsInstance(scale.meta, NumberMeta)
        assert scale.meta.dtype == "float64"
        assert scale.meta.tags == [
            "group:outputs", "widget:textinput", "config:1"]

        offset = o.parts["OUT.OFFSET"]
        assert offset.block_name == "ADDER1"
        assert offset.field_name == "OUT.OFFSET"
        assert offset.meta.writeable == True
        self.assertIsInstance(offset.meta, NumberMeta)
        assert offset.meta.dtype == "float64"
        assert offset.meta.tags == [
            "group:outputs", "widget:textinput", "config:1"]

        capture = o.parts["OUT.CAPTURE"]
        assert capture.block_name == "ADDER1"
        assert capture.field_name == "OUT.CAPTURE"
        assert capture.meta.writeable == True
        self.assertIsInstance(capture.meta, ChoiceMeta)
        assert capture.meta.tags == [
            "group:outputs", "widget:combo", "config:1"]
        assert capture.meta.choices == ["No", "Capture"]

        data_delay = o.parts["OUT.DATA_DELAY"]
        assert data_delay.block_name == "ADDER1"
        assert data_delay.field_name == "OUT.DATA_DELAY"
        assert data_delay.meta.writeable == True
        self.assertIsInstance(data_delay.meta, NumberMeta)
        assert data_delay.meta.dtype == "uint8"
        assert data_delay.meta.tags == [
            "group:outputs", "widget:textinput", "config:1"]

        scale = o.parts["OUT.SCALED"]
        assert scale.block_name == "ADDER1"
        assert scale.meta.writeable == False
        self.assertIsInstance(scale.meta, NumberMeta)
        assert scale.meta.dtype == "float64"
        assert scale.meta.tags == [
            "group:outputs", "widget:textupdate"]

    def test_block_fields_pulse(self):
        fields = OrderedDict()
        block_data = BlockData(4, "Pulse description", fields)
        fields["DELAY"] = FieldData("time", "", "Time", [])
        fields["INP"] = FieldData("bit_mux", "", "Input", ["X.OUT", "Y.OUT"])
        fields["OUT"] = FieldData("bit_out", "", "Output", [])
        fields["ERR_PERIOD"] = FieldData("read", "bit", "Error", [])
        o = PandABlocksMaker(self.client, "PULSE2", block_data)
        assert list(o.parts) == [
            'icon',
            'label',
            'parameters',
            'DELAY',
            'DELAY.UNITS',
            'inputs',
            'INP',
            'INP.CURRENT',
            'INP.DELAY',
            'outputs',
            'OUT',
            'readbacks',
            'ERR_PERIOD']

        delay = o.parts["DELAY"]
        assert delay.block_name == "PULSE2"
        assert delay.field_name == "DELAY"
        assert delay.meta.writeable == True
        self.assertIsInstance(delay.meta, NumberMeta)
        assert delay.meta.dtype == "float64"
        assert delay.meta.tags == [
            "group:parameters", "widget:textinput", "config:2"]

        units = o.parts["DELAY.UNITS"]
        assert units.block_name == "PULSE2"
        assert units.field_name == "DELAY.UNITS"
        assert units.meta.writeable == True
        self.assertIsInstance(units.meta, ChoiceMeta)
        assert units.meta.tags == [
            "group:parameters", "widget:combo", "config:1"]
        assert units.meta.choices == ["s", "ms", "us"]

        inp = o.parts["INP"]
        assert inp.block_name == "PULSE2"
        assert inp.field_name == "INP"
        assert inp.meta.writeable == True
        self.assertIsInstance(inp.meta, ChoiceMeta)
        assert inp.meta.tags == [
            "group:inputs", "inport:bool:ZERO", "widget:combo", "config:1"]
        assert inp.meta.choices == ["X.OUT", "Y.OUT"]

        val = o.parts["INP.CURRENT"]
        assert val.block_name == "PULSE2"
        assert val.meta.writeable == False
        self.assertIsInstance(val.meta, BooleanMeta)
        assert val.meta.tags == [
            "group:inputs", "widget:led"]

        delay = o.parts["INP.DELAY"]
        assert delay.block_name == "PULSE2"
        assert delay.field_name == "INP.DELAY"
        assert delay.meta.writeable == True
        self.assertIsInstance(delay.meta, NumberMeta)
        assert delay.meta.dtype == "uint8"
        assert delay.meta.tags == [
            "group:inputs", "widget:textinput", "config:1"]

        out = o.parts["OUT"]
        assert out.block_name == "PULSE2"
        assert out.field_name == "OUT"
        assert out.meta.writeable == False
        self.assertIsInstance(out.meta, BooleanMeta)
        assert out.meta.tags == [
            "group:outputs", "outport:bool:PULSE2.OUT", "widget:led"]

        err = o.parts["ERR_PERIOD"]
        assert err.block_name == "PULSE2"
        assert err.field_name == "ERR_PERIOD"
        assert err.meta.writeable == False
        self.assertIsInstance(err.meta, BooleanMeta)
        assert err.meta.tags == [
            "group:readbacks", "widget:led"]
