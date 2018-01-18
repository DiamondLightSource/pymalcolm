from malcolm.core import Part, PartRegistrar, ChoiceMeta, Hook
from ..util import CaToolsHelper, CAAttribute, APartName, AMetaDescription, \
    APv, ARbv, ARbvSuff, AMinDelta, ATimeout, AInPort, AWidget, AGroup, AConfig


class CAChoicePart(Part):
    """Defines a choice `Attribute` that talks to a DBR_ENUM mbbo PV"""

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
        super(CAChoicePart, self).__init__(name)
        catools = CaToolsHelper.instance()
        self.meta = ChoiceMeta(description)
        self.caa = CAAttribute(
            self.meta, catools.DBR_ENUM, pv, rbv, rbv_suff, min_delta, timeout,
            inport, widget, group, config, self.on_connect)

    def on_connect(self, value):
        self.meta.set_choices(value.enums)

    def caput(self, value):
        try:
            value = self.attr.meta.choices.index(value)
        except ValueError:
            # Already have the index
            pass
        self.caa.caput(value)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.caa.attr, self.caput)

    def on_hook(self, hook):
        # type: (Hook) -> None
        self.caa.on_hook(hook)
