from malcolm.modules.builtin.vmetas import NumberArrayMeta
from .caarraypart import CAArrayPart


class CADoubleArrayPart(CAArrayPart):
    """Defines a float64[] `Attribute` that talks to a DBR_DOUBLE waveform PV"""

    def create_meta(self, description, tags):
        return NumberArrayMeta("float64", description=description, tags=tags)

    def get_datatype(self):
        return self.catools.DBR_DOUBLE
