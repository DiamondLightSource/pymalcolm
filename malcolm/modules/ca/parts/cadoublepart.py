from cothread import catools

from malcolm.modules.builtin.vmetas import NumberMeta
from .capart import CAPart


class CADoublePart(CAPart):
    """ Defines a part which connects to a pv via channel access DBR_DOUBLE"""

    def create_meta(self, description, tags):
        return NumberMeta("float64", description=description, tags=tags)

    def get_datatype(self):
        return catools.DBR_DOUBLE
