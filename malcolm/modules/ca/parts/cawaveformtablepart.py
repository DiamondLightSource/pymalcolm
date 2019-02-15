from malcolm.core import Part, Widget, PartRegistrar, NumberArrayMeta, \
    TableMeta, DEFAULT_TIMEOUT, Display, BadValueError
from .. import util


class CAWaveformTablePart(Part):
    """Defines a float64[] `Attribute` that talks to multiple DBR_DOUBLE
    waveform PV, plus checks HOPR & LOPR on these PVs to determine axis limits
    """

    def __init__(self,
                 name,  # type: util.APartName
                 description,  # type: util.AMetaDescription
                 pv_list=(),  # type: util.APvList
                 name_list=(),  # type: util.ANameList
                 min_delta=0.05,  # type: util.AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: util.ATimeout
                 widget=Widget.PLOT,  # type: util.AWidget
                 group=None,  # type: util.AGroup
                 config=True,  # type: util.AConfig
                 display_from_pv=True  # type: util.AGetLimits
                 ):
        # type: (...) -> None
        if len(pv_list) != len(name_list):
            raise BadValueError(
                "List of PVs must be same length as list of names!")
        super(CAWaveformTablePart, self).__init__(name)
        self.display_from_pv = display_from_pv
        elements = {}
        for name in name_list:
            elements[name] = NumberArrayMeta(
                "float64", name, tags=[Widget.TEXTUPDATE.tag()])
        self.name_list = name_list
        self.pv_list = pv_list
        self.caa = util.WaveformTableAttribute(
            TableMeta(
                description,
                writeable=False,
                elements=elements),
            util.catools.DBR_DOUBLE, pv_list, name_list, min_delta, timeout,
            widget, group, config, on_connect=self._update_display)

    def _update_display(self, connected_pv):
        if self.display_from_pv:
            el = [ind for ind in range(len(self.pv_list))
                  if self.pv_list[ind] == connected_pv.name]
            if len(el) == 1:
                display = Display(
                    limitHigh=connected_pv.upper_disp_limit,
                    limitLow=connected_pv.lower_disp_limit,
                    precision=connected_pv.precision,
                    units=connected_pv.units
                )
                self.caa.attr.meta.elements[self.name_list[el[0]]].set_display(
                    display)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked)
