from malcolm.core import Part, Registrar
from malcolm.core.vmetas import ChoiceMeta
from ..util import CaToolsHelper, CAAttribute, Name, Description, Pv, Rbv, \
    RbvSuff, MinDelta, Timeout, InPort, AWidget, Group, Config


class CAChoicePart(Part):
    """Defines a choice `Attribute` that talks to a DBR_ENUM mbbo PV"""
    def __init__(self,
                 name,  # type: Name
                 description,  # type: Description
                 pv="",  # type: Pv
                 rbv="",  # type: Rbv
                 rbvSuff="",  # type: RbvSuff
                 minDelta=0.05,  # type: MinDelta
                 timeout=5.0,  # type: Timeout
                 inport=None,  # type: InPort
                 widget=None,  # type: AWidget
                 group=None,  # type: Group
                 config=True,  # type: Config
                 ):
        # type: (...) -> None
        super(CAChoicePart, self).__init__(name)
        catools = CaToolsHelper.instance()
        self.meta = ChoiceMeta(description)
        self.caa = CAAttribute(
            self.meta, catools.DBR_ENUM, pv, rbv, rbvSuff, minDelta, timeout,
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
        # type: (Registrar) -> None
        self.ca.attach_hooks(registrar)
        registrar.add_attribute_model(self.name, self.caa.attr, self.caput)
