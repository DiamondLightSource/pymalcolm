from malcolm.core import Part, PartRegistrar, NumberMeta, DEFAULT_TIMEOUT
from .. import util


class CADoublePart(Part):
    """Defines a float64 `Attribute` that talks to a DBR_DOUBLE ao PV"""

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
        super(CADoublePart, self).__init__(name)
        self.caa = util.CAAttribute(
            NumberMeta("float64", description), util.catools.DBR_DOUBLE, pv,
            rbv, rbv_suffix, min_delta, timeout, sink_port, widget, group,
            config)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked)
