from annotypes import Array

from malcolm.core import DEFAULT_TIMEOUT, Display, NumberArrayMeta, Part, PartRegistrar

from .. import util


class CADoubleArrayPart(Part):
    """Defines a float64[] `Attribute` that talks to a DBR_DOUBLE waveform PV"""

    def __init__(
        self,
        name: util.APartName,
        description: util.AMetaDescription,
        pv: util.APv = "",
        rbv: util.ARbv = "",
        rbv_suffix: util.ARbvSuffix = "",
        min_delta: util.AMinDelta = 0.05,
        timeout: util.ATimeout = DEFAULT_TIMEOUT,
        sink_port: util.ASinkPort = None,
        widget: util.AWidget = None,
        group: util.AGroup = None,
        config: util.AConfig = True,
        display_from_pv: util.AGetLimits = True,
    ) -> None:
        super().__init__(name)
        self.display_from_pv = display_from_pv

        self.caa = util.CAAttribute(
            NumberArrayMeta("float64", description),
            util.catools.DBR_DOUBLE,
            pv,
            rbv,
            rbv_suffix,
            min_delta,
            timeout,
            sink_port,
            widget,
            group,
            config,
            on_connect=self._update_display,
        )

    def _update_display(self, connected_pv):
        if self.display_from_pv:
            display = Display(
                limitHigh=connected_pv.upper_disp_limit,
                limitLow=connected_pv.lower_disp_limit,
                precision=connected_pv.precision,
                units=connected_pv.units,
            )
            self.caa.attr.meta.set_display(display)

    def setup(self, registrar: PartRegistrar) -> None:
        self.caa.setup(registrar, self.name, self.register_hooked, self.caput)

    def caput(self, value):
        if isinstance(value, Array):
            # Unwrap the array before passing to numpy in case it was already
            # a numpy array
            value = value.seq
        self.caa.caput(value)
