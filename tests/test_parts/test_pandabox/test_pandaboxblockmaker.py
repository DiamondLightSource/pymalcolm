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
        self.assertEqual(group.params.writeable, True)
        self.assertIsInstance(group.meta, BooleanMeta)
        self.assertEqual(group.meta.tags, ["widget:group"])
        self.assertEqual(group.control, self.control)
        self.assertEqual(group.process, self.process)

        inpa = o.parts["INPA"]
        self.assertEqual(inpa.params.block_name, "ADDER1")
        self.assertEqual(inpa.params.field_name, "INPA")
        self.assertEqual(inpa.params.writeable, True)
        self.assertIsInstance(inpa.meta, ChoiceMeta)
        self.assertEqual(inpa.meta.tags, [
            "group:inputs", "flowgraph:inport:pos", "widget:combo"])
        self.assertEqual(inpa.meta.choices, ["A.OUT", "B.OUT"])

        val = o.parts["INPA.VAL"]
        self.assertEqual(val.params.block_name, "ADDER1")
        self.assertEqual(val.params.writeable, False)
        self.assertIsInstance(val.meta, NumberMeta)
        self.assertEqual(val.meta.dtype, "float64")
        self.assertEqual(val.meta.tags, [
            "group:inputs", "widget:textupdate"])

        valb = o.parts["INPB"]
        self.assertEqual(valb.params.field_name, "INPB")

        divide = o.parts["DIVIDE"]
        self.assertEqual(divide.params.block_name, "ADDER1")
        self.assertEqual(divide.params.field_name, "DIVIDE")
        self.assertEqual(divide.params.writeable, True)
        self.assertIsInstance(divide.meta, ChoiceMeta)
        self.assertEqual(divide.meta.tags, [
            "group:parameters", "widget:combo"])
        self.assertEqual(divide.meta.choices, ["/1", "/2", "/4"])

        out = o.parts["OUT"]
        self.assertEqual(out.params.block_name, "ADDER1")
        self.assertEqual(out.params.field_name, "OUT")
        self.assertEqual(out.params.writeable, False)
        self.assertIsInstance(out.meta, NumberMeta)
        self.assertEqual(out.meta.dtype, "float64")
        self.assertEqual(out.meta.tags, [
            "group:outputs", "flowgraph:outport:pos", "widget:textupdate"])

        units = o.parts["OUT.UNITS"]
        self.assertEqual(units.params.block_name, "ADDER1")
        self.assertEqual(units.params.field_name, "OUT.UNITS")
        self.assertEqual(units.params.writeable, True)
        self.assertIsInstance(units.meta, StringMeta)
        self.assertEqual(units.meta.tags, [
            "group:outputs", "widget:textinput"])

        scale = o.parts["OUT.SCALE"]
        self.assertEqual(scale.params.block_name, "ADDER1")
        self.assertEqual(scale.params.field_name, "OUT.SCALE")
        self.assertEqual(scale.params.writeable, True)
        self.assertIsInstance(scale.meta, NumberMeta)
        self.assertEqual(scale.meta.dtype, "float64")
        self.assertEqual(scale.meta.tags, [
            "group:outputs", "widget:textinput"])

        offset = o.parts["OUT.OFFSET"]
        self.assertEqual(offset.params.block_name, "ADDER1")
        self.assertEqual(offset.params.field_name, "OUT.OFFSET")
        self.assertEqual(offset.params.writeable, True)
        self.assertIsInstance(offset.meta, NumberMeta)
        self.assertEqual(offset.meta.dtype, "float64")
        self.assertEqual(offset.meta.tags, [
            "group:outputs", "widget:textinput"])

        capture = o.parts["OUT.CAPTURE"]
        self.assertEqual(capture.params.block_name, "ADDER1")
        self.assertEqual(capture.params.field_name, "OUT.CAPTURE")
        self.assertEqual(capture.params.writeable, True)
        self.assertIsInstance(capture.meta, ChoiceMeta)
        self.assertEqual(capture.meta.tags, [
            "group:outputs", "widget:combo"])
        self.assertEqual(capture.meta.choices, ["No", "Capture"])

        data_delay = o.parts["OUT.DATA_DELAY"]
        self.assertEqual(data_delay.params.block_name, "ADDER1")
        self.assertEqual(data_delay.params.field_name, "OUT.DATA_DELAY")
        self.assertEqual(data_delay.params.writeable, True)
        self.assertIsInstance(data_delay.meta, NumberMeta)
        self.assertEqual(data_delay.meta.dtype, "uint8")
        self.assertEqual(data_delay.meta.tags, [
            "group:outputs", "widget:textinput"])

    def test_block_fields_pulse(self):
        fields = OrderedDict()
        block_data = BlockData(4, "Pulse description", fields)
        fields["DELAY"] = FieldData("time", "", "Time", [])
        fields["INP"] = FieldData("bit_mux", "", "Input", ["X.OUT", "Y.OUT"])
        fields["OUT"] = FieldData("bit_out", "", "Output", [])
        fields["ERR_PERIOD"] = FieldData("read", "bit", "Error", [])
        o = PandABoxBlockMaker(self.process, self.control, "PULSE2", block_data)
        self.assertEqual(list(o.parts), [
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
        self.assertEqual(delay.params.block_name, "PULSE2")
        self.assertEqual(delay.params.field_name, "DELAY")
        self.assertEqual(delay.params.writeable, True)
        self.assertIsInstance(delay.meta, NumberMeta)
        self.assertEqual(delay.meta.dtype, "float64")
        self.assertEqual(delay.meta.tags, [
            "group:parameters", "widget:textupdate"])

        units = o.parts["DELAY.UNITS"]
        self.assertEqual(units.params.block_name, "PULSE2")
        self.assertEqual(units.params.field_name, "DELAY.UNITS")
        self.assertEqual(units.params.writeable, True)
        self.assertIsInstance(units.meta, ChoiceMeta)
        self.assertEqual(units.meta.tags, [
            "group:parameters", "widget:combo"])
        self.assertEqual(units.meta.choices, ["s", "ms", "us"])

        inp = o.parts["INP"]
        self.assertEqual(inp.params.block_name, "PULSE2")
        self.assertEqual(inp.params.field_name, "INP")
        self.assertEqual(inp.params.writeable, True)
        self.assertIsInstance(inp.meta, ChoiceMeta)
        self.assertEqual(inp.meta.tags, [
            "group:inputs", "flowgraph:inport:bit", "widget:combo"])
        self.assertEqual(inp.meta.choices, ["X.OUT", "Y.OUT"])

        val = o.parts["INP.VAL"]
        self.assertEqual(val.params.block_name, "PULSE2")
        self.assertEqual(val.params.writeable, False)
        self.assertIsInstance(val.meta, BooleanMeta)
        self.assertEqual(val.meta.tags, [
            "group:inputs", "widget:led"])

        delay = o.parts["INP.DELAY"]
        self.assertEqual(delay.params.block_name, "PULSE2")
        self.assertEqual(delay.params.field_name, "INP.DELAY")
        self.assertEqual(delay.params.writeable, True)
        self.assertIsInstance(delay.meta, NumberMeta)
        self.assertEqual(delay.meta.dtype, "uint8")
        self.assertEqual(delay.meta.tags, [
            "group:inputs", "widget:textinput"])

        out = o.parts["OUT"]
        self.assertEqual(out.params.block_name, "PULSE2")
        self.assertEqual(out.params.field_name, "OUT")
        self.assertEqual(out.params.writeable, False)
        self.assertIsInstance(out.meta, BooleanMeta)
        self.assertEqual(out.meta.tags, [
            "group:outputs", "flowgraph:outport:bit", "widget:led"])

        err = o.parts["ERR_PERIOD"]
        self.assertEqual(err.params.block_name, "PULSE2")
        self.assertEqual(err.params.field_name, "ERR_PERIOD")
        self.assertEqual(err.params.writeable, False)
        self.assertIsInstance(err.meta, BooleanMeta)
        self.assertEqual(err.meta.tags, [
            "group:readbacks", "widget:led"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
