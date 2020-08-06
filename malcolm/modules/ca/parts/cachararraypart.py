from malcolm.core import DEFAULT_TIMEOUT, Part, PartRegistrar, StringMeta

from .. import util


class CACharArrayPart(Part):
    """Defines a string `Attribute` that talks to a DBR_CHAR_STR waveform PV"""

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
            StringMeta(description),
            util.catools.DBR_CHAR_STR,
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
        self.caa.setup(registrar, self.name, self.register_hooked)
