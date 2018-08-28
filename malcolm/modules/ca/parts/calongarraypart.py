from annotypes import Array

from malcolm.core import Part, PartRegistrar, NumberArrayMeta, DEFAULT_TIMEOUT
from ..util import CaToolsHelper, CAAttribute, APartName, AMetaDescription, \
    APv, ARbv, ARbvSuffix, AMinDelta, ATimeout, ASinkPort, AWidget, \
    AGroup, AConfig


class CALongArrayPart(Part):
    """Defines an int32[] `Attribute` that talks to a DBR_LONG waveform PV"""

    def __init__(self,
                 name,  # type: APartName
                 description,  # type: AMetaDescription
                 pv="",  # type: APv
                 rbv="",  # type: ARbv
                 rbv_suffix="",  # type: ARbvSuffix
                 min_delta=0.05,  # type: AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: ATimeout
                 sink_port=None,  # type: ASinkPort
                 widget=None,  # type: AWidget
                 group=None,  # type: AGroup
                 config=True,  # type: AConfig
                 ):
        # type: (...) -> None
        super(CALongArrayPart, self).__init__(name)
        catools = CaToolsHelper.instance()
        self.caa = CAAttribute(
            NumberArrayMeta("int32", description), catools.DBR_LONG, pv, rbv,
            rbv_suffix, min_delta, timeout, sink_port, widget, group, config)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked, self.caput)

    def caput(self, value):
        if isinstance(value, Array):
            # Unwrap the array before passing to numpy in case it was already
            # a numpy array
            value = value.seq
        self.caa.caput(value)
