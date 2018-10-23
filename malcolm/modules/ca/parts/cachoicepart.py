from malcolm.core import Part, PartRegistrar, ChoiceMeta, DEFAULT_TIMEOUT
from .. import util


class CAChoicePart(Part):
    """Defines a choice `Attribute` that talks to a DBR_ENUM mbbo PV"""

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
                 ):
        # type: (...) -> None
        super(CAChoicePart, self).__init__(name)
        self.meta = ChoiceMeta(description)
        self.caa = util.CAAttribute(
            self.meta, util.catools.DBR_ENUM, pv, rbv, rbv_suffix, min_delta,
            timeout, sink_port, widget, group, config, self.on_connect)

    def on_connect(self, value):
        self.meta.set_choices(value.enums)

    def caput(self, value):
        # Turn the string value int the index of the choice list. We are
        # passed a validated value, so it is guaranteed to be in choices
        value = self.meta.choices.index(value)
        self.caa.caput(value)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name, self.register_hooked, self.caput)
