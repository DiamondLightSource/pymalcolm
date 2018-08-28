from malcolm.core import Part, PartRegistrar, ChoiceMeta, DEFAULT_TIMEOUT
from ..util import CaToolsHelper, CAAttribute, APartName, AMetaDescription, \
    APv, ARbv, ARbvSuffix, AMinDelta, ATimeout, ASinkPort, AWidget, \
    AGroup, AConfig


class CAChoicePart(Part):
    """Defines a choice `Attribute` that talks to a DBR_ENUM mbbo PV"""

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
        super(CAChoicePart, self).__init__(name)
        catools = CaToolsHelper.instance()
        self.meta = ChoiceMeta(description)
        self.caa = CAAttribute(
            self.meta, catools.DBR_ENUM, pv, rbv, rbv_suffix, min_delta, timeout,
            sink_port, widget, group, config, self.on_connect)

    def on_connect(self, value):
        self.meta.set_choices(value.enums)

    def caput(self, value):
        # Turn the string value int the index of the choice list. We are
        # passed a validated value, so it is guaranteed to be in choices
        value = self.meta.choices.index(value)
        self.caa.caput(value)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked, self.caput)
