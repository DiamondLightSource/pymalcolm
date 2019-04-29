import unittest
from mock import MagicMock
from xml.etree import cElementTree as ET

from malcolm.modules.pandablocks.parts.pandaluticonpart import \
    PandALutIconPart, get_lut_icon_elements


class PandABLutIconTest(unittest.TestCase):
    def setUp(self):
        self.o = PandALutIconPart(MagicMock(), "LUT1", "")

    def test_lut_elements(self):
        # LUT symbol
        assert get_lut_icon_elements(0) == {
            'AND', 'NOT', 'OR', 'notA', 'notB', 'notC', 'notD', 'notE'}
        # A&B&C&D&E
        assert get_lut_icon_elements(0x80000000) == {
            'LUT', 'NOT', 'OR', 'notA', 'notB', 'notC', 'notD', 'notE'}
        # !A&!B&!C&!D&!E
        assert get_lut_icon_elements(0x1) == {
            'LUT', 'NOT', 'OR'}
        # A&!B
        assert get_lut_icon_elements(0xff0000) == {
            'C', 'D', 'E', 'LUT', 'NOT', 'OR', 'notA', 'notC', 'notD', 'notE'}
        # A&C should be LUT
        assert get_lut_icon_elements(0xf0f00000) == {
             'AND', 'NOT', 'OR', 'notA', 'notB', 'notC', 'notD', 'notE'}
        # !C
        assert get_lut_icon_elements(0xf0f0f0f) == {
            'A', 'AND', 'B', 'D', 'E', 'LUT', 'OR', 'notA', 'notB', 'notC', 'notD', 'notE'}\
        # A|B
        assert get_lut_icon_elements(0xffffff00) == {
            'AND', 'C', 'D', 'E', 'LUT', 'NOT', 'notA', 'notB', 'notC', 'notD', 'notE'}

    def test_symbol(self):
        # !A&!B&!C&!D&!E
        self.o.client.get_field.return_value = "1"
        self.o.update_icon({})
        self.o.client.get_field.assert_called_once_with("LUT1", "FUNC.RAW")
        svg_text = self.o.attr.value
        root = ET.fromstring(svg_text)
        assert len(root.findall(".//*[@id='A']")) == 1
        assert len(root.findall(".//*[@id='notA']")) == 1
        assert len(root.findall(".//*[@id='OR']")) == 0
        assert len(root.findall(".//*[@id='AND']")) == 1
