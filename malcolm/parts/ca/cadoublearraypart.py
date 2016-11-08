from malcolm.core.vmetas import NumberArrayMeta
from malcolm.parts.ca.caarraypart import CAArrayPart


class CADoubleArrayPart(CAArrayPart):
    """ Defines a part which connects to a pv via channel access DBR_DOUBLE"""

    def create_meta(self, description, tags):
        return NumberArrayMeta("float64", description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_DOUBLE
