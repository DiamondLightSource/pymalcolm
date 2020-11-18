from annotypes import Array

from malcolm.core import DEFAULT_TIMEOUT, NumberArrayMeta, Part, PartRegistrar

from .. import util


class CALongArrayPart(Part):
    """Defines an int32[] `Attribute` that talks to a DBR_LONG waveform PV"""

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
    ) -> None:
        super().__init__(name)
        self.caa = util.CAAttribute(
            NumberArrayMeta("int32", description),
            util.catools.DBR_LONG,
            pv,
            rbv,
            rbv_suffix,
            min_delta,
            timeout,
            sink_port,
            widget,
            group,
            config,
        )

    def setup(self, registrar: PartRegistrar) -> None:
        self.caa.setup(registrar, self.name, self.register_hooked, self.caput)

    def caput(self, value):
        if isinstance(value, Array):
            # Unwrap the array before passing to numpy in case it was already
            # a numpy array
            value = value.seq
        self.caa.caput(value)
