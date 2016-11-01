from cothread import catools

from malcolm.core.vmetas import BooleanMeta
from malcolm.parts.ca.capart import CAPart


class CABooleanPart(CAPart):
    """ Defines a part which connects to a pv via channel access DBR_LONG"""

    def create_meta(self, description, tags):
        return BooleanMeta(description=description, tags=tags)

    def get_datatype(self):
        return catools.DBR_LONG

    def caput(self, value):
        value = int(value)
        super(CABooleanPart, self).caput(value)
