from malcolm.core.vmetas import NumberMeta
from malcolm.parts.ca.capart import CAPart


class CALongPart(CAPart):
    """ Defines a part which connects to a pv via channel access DBR_LONG"""

    def create_meta(self, description, tags):
        return NumberMeta("int32", description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_LONG
