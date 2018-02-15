from annotypes import Anno, Array, Union, Sequence

from malcolm.core import Part, StringArrayMeta, Widget, config_tag, \
    PartRegistrar, APartName

with Anno("Initial value for set of axes that can be moved at the same time"):
    ASimultaneousAxes = Array[str]
USimultaneousAxes = Union[ASimultaneousAxes, Sequence[str], str]


class SimultaneousAxesPart(Part):
    def __init__(self, name, value):
        # type: (APartName, USimultaneousAxes) -> None
        super(SimultaneousAxesPart, self).__init__(name)
        self.attr = StringArrayMeta(
            "Set of axes that can be specified in axesToMove at configure",
            tags=[Widget.TABLE.tag(), config_tag()]
        ).create_attribute_model(value)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(
            "simultaneousAxes", self.attr, self.attr.set_value)
