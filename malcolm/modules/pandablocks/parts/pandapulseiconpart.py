from malcolm.modules import builtin
from .pandaiconpart import PandAIconPart


class PandAPulseIconPart(PandAIconPart):
    update_fields = {"TRIG_EDGE"}

    def update_icon(self, icon, field_values):
        # type: (builtin.util.SVGIcon, dict) -> None
        """Update the icon using the given field values"""
        edge = field_values.get("TRIG_EDGE", "rising")
        icon.update_edge_arrow("edge", edge)
