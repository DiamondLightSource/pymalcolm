from malcolm.modules.builtin.vmetas import BooleanMeta
from .capart import CAPart


class CABooleanPart(CAPart):
    """ Defines a part which connects to a pv via channel access DBR_LONG"""

    def create_meta(self, description, tags):
        return BooleanMeta(description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_LONG

    def caput(self, value):
        value = int(value)
        super(CABooleanPart, self).caput(value)
