from annotypes import add_call_types
from scanpointgenerator import CompoundGenerator, SquashingExcluder

from malcolm.core import AMri, APartName, PartRegistrar
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.builtin.parts.childpart import AStateful, UInitialVisibility

from ..hooks import AAxesToMove, AGenerator, UParameterTweakInfos, ValidateHook
from ..infos import ParameterTweakInfo


class UnrollingPart(ChildPart):
    """Unroll the dimensions described by axesToMove into one long line by
    inserting a SquashingExcluder into the generator. This is used for instance
    in Odin to unroll a snake scan into a long line so the VDS is performant
    """

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        initial_visibility: UInitialVisibility = None,
        stateful: AStateful = False,
    ) -> None:
        super().__init__(name, mri, initial_visibility, stateful)

    # This will be serialized, so maintain camelCase for axesToMove
    # noinspection PyPep8Naming
    @add_call_types
    def on_validate(
        self, generator: AGenerator, axesToMove: AAxesToMove
    ) -> UParameterTweakInfos:
        if not self.visible:
            return None

        if len(axesToMove) in (0, 1):
            # We can't have multiple dimensions here, so this must be ok
            return None
        # Check that we have a Squashing excluder in the generator which
        # contains all the axesToMove
        for excluder in generator.excluders:
            if isinstance(excluder, SquashingExcluder) and set(excluder.axes) == set(
                axesToMove
            ):
                # We have already squashed the axes, so nothing to do
                return None
        # We need to squash any dimension containing axesToMove down
        serialized = dict(generator.to_dict())
        serialized["excluders"] = list(serialized["excluders"]) + [
            SquashingExcluder(axes=axesToMove)
        ]
        new_generator = CompoundGenerator.from_dict(serialized)
        return ParameterTweakInfo("generator", new_generator)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(ValidateHook, self.on_validate)
