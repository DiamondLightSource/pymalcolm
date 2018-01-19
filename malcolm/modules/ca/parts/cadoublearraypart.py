from annotypes import Array

from malcolm.core import Part, PartRegistrar, NumberArrayMeta, Hook
from ..util import CaToolsHelper, CAAttribute, APartName, AMetaDescription, \
    APv, ARbv, ARbvSuff, AMinDelta, ATimeout, AInPort, AWidget, AGroup, AConfig


class CADoubleArrayPart(Part):
    """Defines a float64[] `Attribute` that talks to a DBR_DOUBLE waveform PV"""

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
        super(CADoubleArrayPart, self).__init__(name)
        catools = CaToolsHelper.instance()
        self.caa = CAAttribute(
            NumberArrayMeta("float64", description), catools.DBR_DOUBLE, pv,
            rbv, rbv_suff, min_delta, timeout, inport, widget, group, config)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.caput)

    def caput(self, value):
        if isinstance(value, Array):
            # Unwrap the array before passing to numpy in case it was already
            # a numpy array
            value = value.seq
        self.caa.caput(value)

    def on_hook(self, hook):
        # type: (Hook) -> None
        self.caa.on_hook(hook)
