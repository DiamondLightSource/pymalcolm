from annotypes import Array

from malcolm.core import Part, PartRegistrar, NumberArrayMeta, \
    DEFAULT_TIMEOUT, Display
from .. import util


class CADoubleArrayPart(Part):
    """Defines a float64[] `Attribute` that talks to a DBR_DOUBLE waveform PV"""

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
                 display_from_pv=True,  # type: util.AGetLimits
                 ):
        # type: (...) -> None
        super(CADoubleArrayPart, self).__init__(name)
        self.display_from_pv = display_from_pv

        self.caa = util.CAAttribute(
            NumberArrayMeta("float64", description), util.catools.DBR_DOUBLE,
            pv, rbv, rbv_suffix, min_delta, timeout, sink_port, widget, group,
            config, on_connect=self._update_display)

    def _update_display(self, connected_pv):
        if self.display_from_pv:
            display = Display(
                limitHigh=connected_pv.upper_disp_limit,
                limitLow=connected_pv.lower_disp_limit,
                precision=connected_pv.precision,
                units=connected_pv.units
            )
            self.caa.attr.meta.set_display(display)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked, self.caput)

    def caput(self, value):
        if isinstance(value, Array):
            # Unwrap the array before passing to numpy in case it was already
            # a numpy array
            value = value.seq
        self.caa.caput(value)
