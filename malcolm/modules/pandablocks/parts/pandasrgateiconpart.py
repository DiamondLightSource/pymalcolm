from malcolm.modules import builtin

from .pandaiconpart import PandAIconPart


class PandASRGateIconPart(PandAIconPart):
    update_fields = {"SET_EDGE", "RST_EDGE"}

    def update_icon(self, icon: builtin.util.SVGIcon, field_values: dict) -> None:
        """Update the icon using the given field values"""
        icon.add_text("SR", x=70, y=32, anchor="middle")
        icon.update_edge_arrow("edgeSet", field_values["SET_EDGE"])
        icon.update_edge_arrow("edgeRst", field_values["RST_EDGE"])
