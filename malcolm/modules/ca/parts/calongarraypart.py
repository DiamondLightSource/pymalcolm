from annotypes import Array

from malcolm.core import Part, PartRegistrar, NumberArrayMeta, DEFAULT_TIMEOUT
from .. import util


class CALongArrayPart(Part):
    """Defines an int32[] `Attribute` that talks to a DBR_LONG waveform PV"""

    def __init__(self,
                 name,  # type: util.APartName
                 description,  # type: util.AMetaDescription
                 pv="",  # type: util.APv
                 rbv="",  # type: util.ARbv
                 rbv_suffix="",  # type: util.ARbvSuffix
                 min_delta=0.05,  # type: util.AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: util.ATimeout
                 sink_port=None,  # type: util.ASinkPort
                 widget=None,  # type: util.AWidget
                 group=None,  # type: util.AGroup
                 config=True,  # type: util.AConfig
                 ):
        # type: (...) -> None
        super(CALongArrayPart, self).__init__(name)
        self.caa = util.CAAttribute(
            NumberArrayMeta("int32", description), util.catools.DBR_LONG, pv,
            rbv, rbv_suffix, min_delta, timeout, sink_port, widget, group,
            config)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked, self.caput)

    def caput(self, value):
        if isinstance(value, Array):
            # Unwrap the array before passing to numpy in case it was already
            # a numpy array
            value = value.seq
        self.caa.caput(value)
