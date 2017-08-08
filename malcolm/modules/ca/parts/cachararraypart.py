from malcolm.modules.builtin.vmetas import StringMeta
from .capart import CAPart


class CACharArrayPart(CAPart):
    """Defines a string `Attribute` that talks to a DBR_CHAR_STR waveform PV"""

    def create_meta(self, description, tags):
        return StringMeta(description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_CHAR_STR

    def format_caput_value(self, value):
        self.log.info("caput -c -w %s -S %s %r",
                      self.params.timeout, self.params.pv, value)
        return value
