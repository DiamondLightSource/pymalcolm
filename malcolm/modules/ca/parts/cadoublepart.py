from malcolm.modules.builtin.vmetas import NumberMeta
from .capart import CAPart


class CADoublePart(CAPart):
    """Defines a float64 `Attribute` that talks to a DBR_DOUBLE ao PV"""

    def create_meta(self, description, tags):
        return NumberMeta("float64", description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_DOUBLE
