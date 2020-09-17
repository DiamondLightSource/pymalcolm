from malcolm.core import DEFAULT_TIMEOUT, ChoiceMeta, Part, PartRegistrar

from .. import util


class CAChoicePart(Part):
    """Defines a choice `Attribute` that talks to a DBR_ENUM mbbo PV"""

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
        self.meta = ChoiceMeta(description)
        self.caa = util.CAAttribute(
            self.meta,
            util.catools.DBR_ENUM,
            pv,
            rbv,
            rbv_suffix,
            min_delta,
            timeout,
            sink_port,
            widget,
            group,
            config,
            self.on_connect,
        )

    def on_connect(self, value):
        self.meta.set_choices(value.enums)

    def caput(self, value):
        # Turn the string value int the index of the choice list. We are
        # passed a validated value, so it is guaranteed to be in choices
        value = self.meta.choices.index(value)
        self.caa.caput(value)

    def setup(self, registrar: PartRegistrar) -> None:
        self.caa.setup(registrar, self.name, self.register_hooked, self.caput)
