from malcolm.core import Part, PartRegistrar, BooleanMeta, DEFAULT_TIMEOUT
from ..util import CaToolsHelper, CAAttribute, APartName, AMetaDescription, \
    APv, ARbv, ARbvSuff, AMinDelta, ATimeout, AInPort, AWidget, AGroup, AConfig


class CABooleanPart(Part):
    """Defines a boolean `Attribute` that talks to a DBR_LONG longout PV"""

    def __init__(self,
                 name,  # type: APartName
                 description,  # type: AMetaDescription
                 pv="",  # type: APv
                 rbv="",  # type: ARbv
                 rbv_suff="",  # type: ARbvSuff
                 min_delta=0.05,  # type: AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: ATimeout
                 inport=None,  # type: AInPort
                 widget=None,  # type: AWidget
                 group=None,  # type: AGroup
                 config=True,  # type: AConfig
                 ):
        # type: (...) -> None
        super(CABooleanPart, self).__init__(name)
        catools = CaToolsHelper.instance()
        self.caa = CAAttribute(
            BooleanMeta(description), catools.DBR_LONG, pv, rbv, rbv_suff,
            min_delta, timeout, inport, widget, group, config)

    def caput(self, value):
        self.caa.caput(int(value))

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked, self.caput)
