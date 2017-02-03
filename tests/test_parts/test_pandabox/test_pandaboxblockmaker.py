import os
import sys
from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import call, Mock

from malcolm.core.vmetas import BooleanMeta, ChoiceMeta, NumberMeta, StringMeta
from malcolm.parts.pandabox.pandaboxblockmaker import PandABoxBlockMaker
from malcolm.parts.pandabox.pandaboxcontrol import BlockData, FieldData


class PandABoxBlockMakerTest(unittest.TestCase):
    def setUp(self):
        self.process = Mock()
        self.control = Mock()

    def test_block_fields_adder(self):
        fields = OrderedDict()
        block_data = BlockData(2, "Adder description", fields)
        fields["INPA"] = FieldData("pos_mux", "", "Input A", ["A.OUT", "B.OUT"])
        fields["INPB"] = FieldData("pos_mux", "", "Input B", ["A.OUT", "B.OUT"])
        fields["DIVIDE"] = FieldData("param", "enum", "Divide output",
                                     ["/1", "/2", "/4"])
        fields["OUT"] = FieldData("pos_out", "", "Output", ["No", "Capture"])
        o = PandABoxBlockMaker(self.process, self.control, "ADDER1", block_data)
        self.assertEqual(list(o.parts), [
            'icon',
            'inputs',
            'INPA',
            'INPA.VAL',
            'INPB',
            'INPB.VAL',
            'parameters',
            'DIVIDE',
            'outputs',
            'OUT',
            'OUT.UNITS',
            'OUT.SCALE',
            'OUT.OFFSET',
            'OUT.CAPTURE',
            'OUT.DATA_DELAY'])

        group = o.parts["inputs"]
        self.assertEqual(group.attr_name, "inputs")
        self.assertEqual(group.process, self.process)
        self.assertEqual(group.meta.tags, ("widget:group", "config"))

        inpa = o.parts["INPA"]
        self.assertEqual(inpa.block_name, "ADDER1")
        self.assertEqual(inpa.field_name, "INPA")
        self.assertEqual(inpa.writeable, True)
        self.assertIsInstance(inpa.meta, ChoiceMeta)
        self.assertEqual(inpa.meta.tags, (
            "group:inputs", "inport:int32:ZERO", "widget:combo", "config"))
        self.assertEqual(inpa.meta.choices, ("A.OUT", "B.OUT"))

        val = o.parts["INPA.VAL"]
        self.assertEqual(val.block_name, "ADDER1")
        self.assertEqual(val.writeable, False)
        self.assertIsInstance(val.meta, NumberMeta)
        self.assertEqual(val.meta.dtype, "float64")
        self.assertEqual(val.meta.tags, (
            "group:inputs", "widget:textupdate"))

        valb = o.parts["INPB"]
        self.assertEqual(valb.field_name, "INPB")

        divide = o.parts["DIVIDE"]
        self.assertEqual(divide.block_name, "ADDER1")
        self.assertEqual(divide.field_name, "DIVIDE")
        self.assertEqual(divide.writeable, True)
        self.assertIsInstance(divide.meta, ChoiceMeta)
        self.assertEqual(divide.meta.tags, (
            "group:parameters", "widget:combo", "config"))
        self.assertEqual(divide.meta.choices, ("/1", "/2", "/4"))

        out = o.parts["OUT"]
        self.assertEqual(out.block_name, "ADDER1")
        self.assertEqual(out.field_name, "OUT")
        self.assertEqual(out.writeable, False)
        self.assertIsInstance(out.meta, NumberMeta)
        self.assertEqual(out.meta.dtype, "float64")
        self.assertEqual(out.meta.tags, (
            "group:outputs", "outport:int32:ADDER1.OUT",
            "widget:textupdate"))

        units = o.parts["OUT.UNITS"]
        self.assertEqual(units.block_name, "ADDER1")
        self.assertEqual(units.field_name, "OUT.UNITS")
        self.assertEqual(units.writeable, True)
        self.assertIsInstance(units.meta, StringMeta)
        self.assertEqual(units.meta.tags, (
            "group:outputs", "widget:textinput", "config"))

        scale = o.parts["OUT.SCALE"]
        self.assertEqual(scale.block_name, "ADDER1")
        self.assertEqual(scale.field_name, "OUT.SCALE")
        self.assertEqual(scale.writeable, True)
        self.assertIsInstance(scale.meta, NumberMeta)
        self.assertEqual(scale.meta.dtype, "float64")
        self.assertEqual(scale.meta.tags, (
            "group:outputs", "widget:textinput", "config"))

        offset = o.parts["OUT.OFFSET"]
        self.assertEqual(offset.block_name, "ADDER1")
        self.assertEqual(offset.field_name, "OUT.OFFSET")
        self.assertEqual(offset.writeable, True)
        self.assertIsInstance(offset.meta, NumberMeta)
        self.assertEqual(offset.meta.dtype, "float64")
        self.assertEqual(offset.meta.tags, (
            "group:outputs", "widget:textinput", "config"))

        capture = o.parts["OUT.CAPTURE"]
        self.assertEqual(capture.block_name, "ADDER1")
        self.assertEqual(capture.field_name, "OUT.CAPTURE")
        self.assertEqual(capture.writeable, True)
        self.assertIsInstance(capture.meta, ChoiceMeta)
        self.assertEqual(capture.meta.tags, (
            "group:outputs", "widget:combo", "config"))
        self.assertEqual(capture.meta.choices, ("No", "Capture"))

        data_delay = o.parts["OUT.DATA_DELAY"]
        self.assertEqual(data_delay.block_name, "ADDER1")
        self.assertEqual(data_delay.field_name, "OUT.DATA_DELAY")
        self.assertEqual(data_delay.writeable, True)
        self.assertIsInstance(data_delay.meta, NumberMeta)
        self.assertEqual(data_delay.meta.dtype, "uint8")
        self.assertEqual(data_delay.meta.tags, (
            "group:outputs", "widget:textinput", "config"))

    def test_block_fields_pulse(self):
        fields = OrderedDict()
        block_data = BlockData(4, "Pulse description", fields)
        fields["DELAY"] = FieldData("time", "", "Time", [])
        fields["INP"] = FieldData("bit_mux", "", "Input", ["X.OUT", "Y.OUT"])
        fields["OUT"] = FieldData("bit_out", "", "Output", [])
        fields["ERR_PERIOD"] = FieldData("read", "bit", "Error", [])
        o = PandABoxBlockMaker(self.process, self.control, "PULSE2", block_data)
        self.assertEqual(list(o.parts), [
            'icon',
            'parameters',
            'DELAY',
            'DELAY.UNITS',
            'inputs',
            'INP',
            'INP.VAL',
            'INP.DELAY',
            'outputs',
            'OUT',
            'readbacks',
            'ERR_PERIOD'])

        delay = o.parts["DELAY"]
        self.assertEqual(delay.block_name, "PULSE2")
        self.assertEqual(delay.field_name, "DELAY")
        self.assertEqual(delay.writeable, True)
        self.assertIsInstance(delay.meta, NumberMeta)
        self.assertEqual(delay.meta.dtype, "float64")
        self.assertEqual(delay.meta.tags, (
            "group:parameters", "widget:textupdate", "config"))

        units = o.parts["DELAY.UNITS"]
        self.assertEqual(units.block_name, "PULSE2")
        self.assertEqual(units.field_name, "DELAY.UNITS")
        self.assertEqual(units.writeable, True)
        self.assertIsInstance(units.meta, ChoiceMeta)
        self.assertEqual(units.meta.tags, (
            "group:parameters", "widget:combo", "config"))
        self.assertEqual(units.meta.choices, ("s", "ms", "us"))

        inp = o.parts["INP"]
        self.assertEqual(inp.block_name, "PULSE2")
        self.assertEqual(inp.field_name, "INP")
        self.assertEqual(inp.writeable, True)
        self.assertIsInstance(inp.meta, ChoiceMeta)
        self.assertEqual(inp.meta.tags, (
            "group:inputs", "inport:bool:ZERO", "widget:combo", "config"))
        self.assertEqual(inp.meta.choices, ("X.OUT", "Y.OUT"))

        val = o.parts["INP.VAL"]
        self.assertEqual(val.block_name, "PULSE2")
        self.assertEqual(val.writeable, False)
        self.assertIsInstance(val.meta, BooleanMeta)
        self.assertEqual(val.meta.tags, (
            "group:inputs", "widget:led"))

        delay = o.parts["INP.DELAY"]
        self.assertEqual(delay.block_name, "PULSE2")
        self.assertEqual(delay.field_name, "INP.DELAY")
        self.assertEqual(delay.writeable, True)
        self.assertIsInstance(delay.meta, NumberMeta)
        self.assertEqual(delay.meta.dtype, "uint8")
        self.assertEqual(delay.meta.tags, (
            "group:inputs", "widget:textinput", "config"))

        out = o.parts["OUT"]
        self.assertEqual(out.block_name, "PULSE2")
        self.assertEqual(out.field_name, "OUT")
        self.assertEqual(out.writeable, False)
        self.assertIsInstance(out.meta, BooleanMeta)
        self.assertEqual(out.meta.tags, (
            "group:outputs", "outport:bool:PULSE2.OUT", "widget:led"))

        err = o.parts["ERR_PERIOD"]
        self.assertEqual(err.block_name, "PULSE2")
        self.assertEqual(err.field_name, "ERR_PERIOD")
        self.assertEqual(err.writeable, False)
        self.assertIsInstance(err.meta, BooleanMeta)
        self.assertEqual(err.meta.tags, (
            "group:readbacks", "widget:led"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
