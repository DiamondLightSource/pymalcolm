from malcolm.modules.builtin.vmetas import NumberMeta
from .capart import CAPart


class CALongPart(CAPart):
    """Defines an int32 `Attribute` that talks to a DBR_LONG longout PV"""

    def create_meta(self, description, tags):
        return NumberMeta("int32", description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_LONG
