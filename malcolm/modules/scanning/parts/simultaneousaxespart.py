from annotypes import Anno, Array, Union, Sequence, add_call_types

from malcolm.core import Part, StringArrayMeta, Widget, config_tag, \
    PartRegistrar, APartName
from ..hooks import ValidateHook, AAxesToMove


with Anno("Initial value for set of axes that can be moved at the same time"):
    ASimultaneousAxes = Array[str]
USimultaneousAxes = Union[ASimultaneousAxes, Sequence[str], str]


class SimultaneousAxesPart(Part):
    def __init__(self, name="simultaneousAxes", value=None):
        # type: (APartName, USimultaneousAxes) -> None
        super(SimultaneousAxesPart, self).__init__(name)
        self.attr = StringArrayMeta(
            "Set of axes that can be specified in axesToMove at configure",
            tags=[Widget.TEXTINPUT.tag(), config_tag()]
        ).create_attribute_model(value)

    # This will be serialized, so maintain camelCase for axesToMove
    # noinspection PyPep8Naming
    @add_call_types
    def validate(self, axesToMove):
        # type: (AAxesToMove) -> None
        assert not set(axesToMove) - set(self.attr.value), \
            "Can only move %s simultaneously, requested %s" % (
                list(self.attr.value), axesToMove)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(
            "simultaneousAxes", self.attr, self.attr.set_value)
        # Hooks
        registrar.hook(ValidateHook, self.validate)
