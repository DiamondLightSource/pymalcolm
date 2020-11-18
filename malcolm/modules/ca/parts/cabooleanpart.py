from malcolm.core import DEFAULT_TIMEOUT, BooleanMeta, Part, PartRegistrar

from .. import util


class CABooleanPart(Part):
    """Defines a boolean `Attribute` that talks to a DBR_LONG longout PV"""

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
        throw: util.AThrow = True,
    ) -> None:
        super().__init__(name)
        self.caa = util.CAAttribute(
            BooleanMeta(description),
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
            throw=throw,
        )

    def caput(self, value):
        self.caa.caput(int(value))

    def setup(self, registrar: PartRegistrar) -> None:
        self.caa.setup(registrar, self.name, self.register_hooked, self.caput)
