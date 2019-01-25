from malcolm.core import Part, Widget, PartRegistrar, NumberArrayMeta, TableMeta, DEFAULT_TIMEOUT, Display
from .. import util


class CAWaveform2DPart(Part):
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
                 display_t_from_pv=False  # type: util.AGetLimits
                 ):
        # type: (...) -> None
        super(CAWaveform2DPart, self).__init__(name)

        def update_display_t(connected_pv):
            if display_t_from_pv:
                el = None
                if connected_pv.name == yData:
                    el = "yData"
                elif connected_pv.name == xData:
                    el = "xData"
                if el is not None:
                    display = self.caa.attr.meta.elements[el].display_t
                    display.set_limitHigh(connected_pv.upper_disp_limit)
                    display.set_limitLow(connected_pv.lower_disp_limit)
                    display.set_precision(connected_pv.precision)
                    display.set_units(connected_pv.units)

        self.caa = util.Waveform2DAttribute(
            TableMeta(
                description,
                writeable=False,
                elements={
                    "xData": NumberArrayMeta("float64", "x data", display_t=Display(), tags=(Widget.TEXTUPDATE.tag(),)),
                    "yData": NumberArrayMeta("float64", "y data", display_t=Display(), tags=(Widget.TEXTUPDATE.tag(),))
                }),
            util.catools.DBR_DOUBLE, yData, xData, min_delta, timeout, sink_port, widget, group, config, on_connect=update_display_t)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked)
