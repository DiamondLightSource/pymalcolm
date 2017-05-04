from malcolm.modules.builtin.vmetas import StringMeta
from .capart import CAPart


class CAStringPart(CAPart):
    """Defines a string `Attribute` that talks to a DBR_STRING stringout PV"""

    def create_meta(self, description, tags):
        return StringMeta(description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_STRING
