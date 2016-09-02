from cothread import catools

from malcolm.core.vmetas import NumberMeta
from malcolm.parts.ca.capart import CAPart, capart_takes


@capart_takes()
class CALongPart(CAPart):
    """ Defines a part which connects to a pv via channel access DBR_LONG"""

    def create_meta(self, description):
        return NumberMeta("int32", description)

    def get_datatype(self):
        return catools.DBR_LONG
