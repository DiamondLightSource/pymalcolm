from cothread import catools

from malcolm.core.vmetas import NumberArrayMeta
from malcolm.parts.ca.capart import CAPart, capart_takes


@capart_takes()
class CADoubleArrayPart(CAPart):
    """ Defines a part which connects to a pv via channel access DBR_DOUBLE"""

    def create_meta(self, description):
        return NumberArrayMeta("float64", description)

    def get_datatype(self):
        return catools.DBR_DOUBLE
