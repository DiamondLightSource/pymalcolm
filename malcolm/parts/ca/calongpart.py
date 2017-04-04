from cothread import catools

from malcolm.parts.ca.capart import CAPart
from malcolm.vmetas.builtin import NumberMeta


class CALongPart(CAPart):
    """ Defines a part which connects to a pv via channel access DBR_LONG"""

    def create_meta(self, description, tags):
        return NumberMeta("int32", description=description, tags=tags)

    def get_datatype(self):
        return catools.DBR_LONG
