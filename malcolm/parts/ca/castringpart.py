from cothread import catools

from malcolm.parts.ca.capart import CAPart
from malcolm.vmetas.builtin import StringMeta


class CAStringPart(CAPart):
    """Defines a part which connects to a pv via channel access DBR_STRING"""

    def create_meta(self, description, tags):
        return StringMeta(description=description, tags=tags)

    def get_datatype(self):
        return catools.DBR_STRING
