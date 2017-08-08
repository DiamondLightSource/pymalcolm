from .capart import CAPart


class CAArrayPart(CAPart):
    """Abstract class with better logging for CAParts with array types"""

    def format_caput_value(self, value):
        l = len(value)
        v = " ".join(str(x) for x in value)
        self.log.info("caput -c -w %s %s -a %d %s",
                      self.params.timeout, self.params.pv, l, v)
        return value
