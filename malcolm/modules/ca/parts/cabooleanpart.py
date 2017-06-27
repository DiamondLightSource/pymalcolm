from malcolm.modules.builtin.vmetas import BooleanMeta
from .capart import CAPart


class CABooleanPart(CAPart):
    """Defines a boolean `Attribute` that talks to a DBR_LONG longout PV"""

    def create_meta(self, description, tags):
        return BooleanMeta(description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_LONG

    def caput(self, value):
        value = int(value)
        super(CABooleanPart, self).caput(value)
