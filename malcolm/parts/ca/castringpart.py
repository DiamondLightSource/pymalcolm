from cothread import catools

from malcolm.core.vmetas import StringMeta
from malcolm.parts.ca.capart import CAPart, capart_takes


@capart_takes()
class CAStringPart(CAPart):
    """Defines a part which connects to a pv via channel access DBR_STRING"""

    def create_meta(self, description):
        return StringMeta(description)

    def get_datatype(self):
        return catools.DBR_STRING
