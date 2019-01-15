from malcolm.core import Part, Widget, PartRegistrar, NumberArrayMeta, TableMeta, DEFAULT_TIMEOUT, Display
from malcolm.modules.ca.util import catools
from .. import util


class Waveform2DPart(Part):
    """Defines a float64[] `Attribute` that talks to a DBR_DOUBLE waveform PV,
     and optionally talks to a second waveform to obtain x axis points
      plus checks HOPR & LOPR on these PVs to determine axis limits"""

    def __init__(self,
                 name,  # type: util.APartName
                 description,  # type: util.AMetaDescription
                 yData="",  # type: util.APv
                 xData="",  # type: util.ARbv
                 min_delta=0.05,  # type: util.AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: util.ATimeout
                 sink_port=None,  # type: util.ASinkPort
                 widget=Widget.PLOT,  # type: util.AWidget
                 group=None,  # type: util.AGroup
                 config=True,  # type: util.AConfig
                 limits_from_pv=False  # type: util.AGetLimits
                 ):
        # type: (...) -> None
        super(Waveform2DPart, self).__init__(name)
        self.caa = util.Waveform2DAttribute(
            TableMeta(
                "2D plot", description,
                elements={
                    "xData": NumberArrayMeta("float64", "x data", display_t=Display()),
                    "yData": NumberArrayMeta("float64", "y data", display_t=Display())
                }),
            catools.DBR_DOUBLE, yData, xData, min_delta, timeout, sink_port, widget, group, config, limits_from_pv)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked)
