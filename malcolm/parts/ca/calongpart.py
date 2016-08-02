from cothread import catools

from malcolm.metas import NumberMeta
from malcolm.parts.ca.capart import CAPart, capart_takes


@capart_takes()
class CADoublePart(CAPart):
    """ Defines a part which connects to a pv via channel access DBR_DOUBLE"""

    def create_meta(self, description):
        return NumberMeta("int32", description)

    def get_datatype(self):
        return catools.DBR_LONG
