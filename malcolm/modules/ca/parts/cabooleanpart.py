from malcolm.core import Part, Registrar
from malcolm.core.vmetas import BooleanMeta
from ..util import CaToolsHelper, CAAttribute, Name, Description, Pv, Rbv, \
    RbvSuff, MinDelta, Timeout, InPort, AWidget, Group, Config


class CABooleanPart(Part):
    """Defines a boolean `Attribute` that talks to a DBR_LONG longout PV"""
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
        super(CABooleanPart, self).__init__(name)
        catools = CaToolsHelper.instance()
        self.caa = CAAttribute(
            BooleanMeta(description), catools.DBR_LONG,
            pv, rbv, rbvSuff, minDelta, timeout, inport, widget, group, config)

    def caput(self, value):
        self.caa.caput(int(value))

    def setup(self, registrar):
        # type: (Registrar) -> None
        self.ca.attach_hooks(registrar)
        registrar.add_attribute_model(self.name, self.caa.attr, self.caput)
