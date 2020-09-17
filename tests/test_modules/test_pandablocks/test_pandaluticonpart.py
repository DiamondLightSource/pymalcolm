import os
import unittest
from xml.etree import cElementTree as ET

from mock import MagicMock

from malcolm.modules.builtin.util import SVGIcon
from malcolm.modules.pandablocks.parts.pandaluticonpart import (
    PandALutIconPart,
    get_lut_icon_elements,
)
from malcolm.modules.pandablocks.util import SVG_DIR


class PandABLutIconTest(unittest.TestCase):
    def setUp(self):
        svg_path = os.path.join(SVG_DIR, "LUT.svg")
        self.o = PandALutIconPart(MagicMock(), "LUT1", svg_path)

    def test_lut_elements(self):
        # LUT symbol
        assert get_lut_icon_elements(0) == {
            "AND",
            "NOT",
            "OR",
            "notA",
            "notB",
            "notC",
            "notD",
            "notE",
        }
        # A&B&C&D&E
        assert get_lut_icon_elements(0x80000000) == {
            "LUT",
            "NOT",
            "OR",
            "notA",
            "notB",
            "notC",
            "notD",
            "notE",
        }
        # !A&!B&!C&!D&!E
        assert get_lut_icon_elements(0x1) == {"LUT", "NOT", "OR"}
        # A&!B
        assert get_lut_icon_elements(0xFF0000) == {
            "C",
            "D",
            "E",
            "LUT",
            "NOT",
            "OR",
            "notA",
            "notC",
            "notD",
            "notE",
            "edgeC",
            "edgeD",
            "edgeE",
        }
        # A&C should be LUT
        assert get_lut_icon_elements(0xF0F00000) == {
            "AND",
            "NOT",
            "OR",
            "notA",
            "notB",
            "notC",
            "notD",
            "notE",
        }
        # !C
        assert get_lut_icon_elements(0xF0F0F0F) == {
            "A",
            "AND",
            "B",
            "D",
            "E",
            "LUT",
            "OR",
            "notA",
            "notB",
            "notC",
            "notD",
            "notE",
            "edgeA",
            "edgeB",
            "edgeD",
            "edgeE",
        }
        # A|B
        assert get_lut_icon_elements(0xFFFFFF00) == {
            "AND",
            "C",
            "D",
            "E",
            "LUT",
            "NOT",
            "notA",
            "notB",
            "notC",
            "notD",
            "notE",
            "edgeC",
            "edgeD",
            "edgeE",
        }

    def test_symbol(self):
        # !A&!B&!C&!D
        self.o.client.get_field.return_value = "0x00000003"
        icon = SVGIcon(self.o.svg_text)
        self.o.update_icon(
            icon,
            dict(
                FUNC="~A&~B&~C&~D",
                TYPEA="level",
                TYPEB="rising",
                TYPEC="falling",
                TYPED="either",
                TYPEE="rising",
            ),
        )
        self.o.client.get_field.assert_called_once_with("LUT1", "FUNC.RAW")
        svg_text = str(icon)
        root = ET.fromstring(svg_text)
        assert len(root.findall(".//*[@id='A']")) == 1
        assert len(root.findall(".//*[@id='notA']")) == 1
        assert len(root.findall(".//*[@id='OR']")) == 0
        assert len(root.findall(".//*[@id='AND']")) == 1
        assert len(root.findall(".//*[@id='edgeA']")) == 0
        edgebs = root.findall(".//*[@id='edgeB']")
        assert len(edgebs) == 1
        assert "marker-end" not in edgebs[0].attrib
        edgecs = root.findall(".//*[@id='edgeC']")
        assert len(edgecs) == 1
        assert "marker-start" not in edgecs[0].attrib
        assert len(root.findall(".//*[@id='edgeD']")) == 1
        assert len(root.findall(".//*[@id='edgeE']")) == 0
        assert root[-1].text == "~A&~B&~C&~D"
