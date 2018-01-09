from malcolm.core import Part, Registrar
from malcolm.core.vmetas import StringMeta
from ..util import CaToolsHelper, CAAttribute, Name, Description, Pv, Rbv, \
    RbvSuff, MinDelta, Timeout, InPort, AWidget, Group, Config


class CAStringPart(Part):
    """Defines a string `Attribute` that talks to a DBR_STRING stringout PV"""
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
        super(CAStringPart, self).__init__(name)
        catools = CaToolsHelper.instance()
        self.caa = CAAttribute(
            StringMeta(description), catools.DBR_LONG,
            pv, rbv, rbvSuff, minDelta, timeout, inport, widget, group, config)

    def setup(self, registrar):
        # type: (Registrar) -> None
        self.ca.attach_hooks(registrar)
        registrar.add_attribute_model(self.name, self.caa.attr, self.caa.caput)
