from malcolm.core import Part, PartRegistrar, StringMeta, DEFAULT_TIMEOUT
from ..util import CaToolsHelper, CAAttribute, APartName, AMetaDescription, \
    APv, ARbv, ARbvSuffix, AMinDelta, ATimeout, ASinkPort, AWidget, \
    AGroup, AConfig


class CACharArrayPart(Part):
    """Defines a string `Attribute` that talks to a DBR_CHAR_STR waveform PV"""

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
        super(CACharArrayPart, self).__init__(name)
        catools = CaToolsHelper.instance()
        self.caa = CAAttribute(
            StringMeta(description), catools.DBR_CHAR_STR, pv, rbv, rbv_suffix,
            min_delta, timeout, sink_port, widget, group, config)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked)
