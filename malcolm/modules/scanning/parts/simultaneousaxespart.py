from typing import Sequence, Union

from annotypes import Anno, Array, add_call_types

from malcolm.core import (
    APartName,
    Part,
    PartRegistrar,
    StringArrayMeta,
    Widget,
    config_tag,
)

from ..hooks import AAxesToMove, ValidateHook

with Anno("Initial value for set of axes that can be moved at the same time"):
    ASimultaneousAxes = Union[Array[str]]
USimultaneousAxes = Union[ASimultaneousAxes, Sequence[str], str]


class SimultaneousAxesPart(Part):
    def __init__(
        self, name: APartName = "simultaneousAxes", value: USimultaneousAxes = None
    ) -> None:
        super().__init__(name)
        self.attr = StringArrayMeta(
            "Set of axes that can be specified in axesToMove at configure",
            tags=[Widget.TEXTINPUT.tag(), config_tag()],
        ).create_attribute_model(value)

    # This will be serialized, so maintain camelCase for axesToMove
    # noinspection PyPep8Naming
    @add_call_types
    def on_validate(self, axesToMove: AAxesToMove) -> None:
        assert not set(axesToMove) - set(
            self.attr.value
        ), "Can only move %s simultaneously, requested %s" % (
            list(self.attr.value),
            axesToMove,
        )

    def setup(self, registrar: PartRegistrar) -> None:
        registrar.add_attribute_model(
            "simultaneousAxes", self.attr, self.attr.set_value
        )
        # Hooks
        registrar.hook(ValidateHook, self.on_validate)
