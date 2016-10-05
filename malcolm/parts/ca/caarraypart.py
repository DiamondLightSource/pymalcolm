from cothread import catools

from malcolm.core.vmetas import NumberArrayMeta
from malcolm.parts.ca.capart import CAPart, capart_takes


class CAArrayPart(CAPart):
    """ Defines a part which connects to a pv via channel access DBR_DOUBLE"""

    def format_caput_value(self, value):
        l = len(value)
        v = " ".join(str(x) for x in value)
        self.log_info("caput -c -w 1000 %s -a %d %s", self.params.pv, l, v)
        return value
