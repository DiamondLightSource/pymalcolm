import os

from malcolm.modules import builtin
from .pandaiconpart import PandAIconPart
from ..util import SVG_DIR


class PandAPulseIconPart(PandAIconPart):
    update_fields = {"DELAY", "DELAY.UNITS", "WIDTH", "WIDTH.UNITS",
                     "STEP", "STEP.UNITS", "PULSES", "TRIG_EDGE"}

    def update_icon(self, field_values, ts):
        """Update the icon using the given field values"""
        with open(os.path.join(SVG_DIR, "PULSE.svg")) as f:
            icon = builtin.util.SVGIcon(f.read())

        edge = field_values.get("TRIG_EDGE", "rising")
        icon.update_edge_arrow("edge", edge)
        self.attr.set_value(str(icon), ts=ts)

