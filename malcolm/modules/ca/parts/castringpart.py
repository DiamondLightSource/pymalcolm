from malcolm.core import Part, PartRegistrar, StringMeta, Hook
from ..util import CaToolsHelper, CAAttribute, APartName, AMetaDescription, \
    APv, ARbv, ARbvSuff, AMinDelta, ATimeout, AInPort, AWidget, AGroup, AConfig


class CAStringPart(Part):
    """Defines a string `Attribute` that talks to a DBR_STRING stringout PV"""

    def __init__(self,
                 name,  # type: APartName
                 description,  # type: AMetaDescription
                 pv="",  # type: APv
                 rbv="",  # type: ARbv
                 rbv_suff="",  # type: ARbvSuff
                 min_delta=0.05,  # type: AMinDelta
                 timeout=5.0,  # type: ATimeout
                 inport=None,  # type: AInPort
                 widget=None,  # type: AWidget
                 group=None,  # type: AGroup
                 config=True,  # type: AConfig
                 ):
        # type: (...) -> None
        super(CAStringPart, self).__init__(name)
        catools = CaToolsHelper.instance()
        self.caa = CAAttribute(
            StringMeta(description), catools.DBR_LONG, pv, rbv, rbv_suff,
            min_delta, timeout, inport, widget, group, config)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.caa.attr, self.caa.caput)

    def on_hook(self, hook):
        # type: (Hook) -> None
        self.caa.on_hook(hook)
