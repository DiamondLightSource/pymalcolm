import os

from malcolm.modules import builtin
from .pandaiconpart import PandAIconPart
from ..util import SVG_DIR


class PandASRGateIconPart(PandAIconPart):
    update_fields = {"SET_EDGE", "RST_EDGE", "OUT"}

    def update_icon(self, field_values, ts):
        """Update the icon using the given field values"""
        with open(os.path.join(SVG_DIR, "SRGATE.svg")) as f:
            icon = builtin.util.SVGIcon(f.read())

        style = "font: 12px mono;%s"
        if field_values["OUT"]:
            r_style, s_style = style % "", style % "text-decoration: underline"
        else:
            s_style, r_style = style % "", style % "text-decoration: underline"
        icon.add_text("S", x=65, y=32, anchor="middle", style=s_style)
        icon.add_text("R", x=75, y=32, anchor="middle", style=r_style)
        icon.update_edge_arrow("edgeSet", field_values["SET_EDGE"])
        icon.update_edge_arrow("edgeRst", field_values["RST_EDGE"])
        self.attr.set_value(str(icon), ts=ts)

