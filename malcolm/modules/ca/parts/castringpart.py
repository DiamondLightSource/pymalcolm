from malcolm.core import Part, PartRegistrar, StringMeta, DEFAULT_TIMEOUT
from .. import util


class CAStringPart(Part):
    """Defines a string `Attribute` that talks to a DBR_STRING stringout PV"""

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
        super(CAStringPart, self).__init__(name)
        self.caa = util.CAAttribute(
            StringMeta(description), util.catools.DBR_STRING, pv, rbv,
            rbv_suffix, min_delta, timeout, sink_port, widget, group, config)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked)

