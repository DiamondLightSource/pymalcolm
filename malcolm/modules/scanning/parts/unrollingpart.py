from annotypes import add_call_types
from scanpointgenerator import CompoundGenerator, SquashingExcluder

from malcolm.core import Part, PartRegistrar
from ..hooks import ValidateHook, AAxesToMove, AGenerator, UParameterTweakInfos
from ..infos import ParameterTweakInfo


class UnrollingPart(Part):
    """Unroll the dimensions described by axesToMove into one long line by
    inserting a SquashingExcluder into the generator. This is used for instance
    in Odin to unroll a snake scan into a long line so the VDS is performant
    """
    # This will be serialized, so maintain camelCase for axesToMove
    # noinspection PyPep8Naming
    @add_call_types
    def validate(self, generator, axesToMove):
        # type: (AGenerator, AAxesToMove) -> UParameterTweakInfos
        if len(axesToMove) in (0, 1):
            # We can't have multiple dimensions here, so this must be ok
            return
        # Check that we have a Squashing excluder in the generator which
        # contains all the axesToMove
        for excluder in generator.excluders:
            if isinstance(excluder, SquashingExcluder) \
                    and set(excluder.axes) == set(axesToMove):
                # We have already squashed the axes, so nothing to do
                return
        # We need to squash any dimension containing axesToMove down
        serialized = dict(generator.to_dict())
        serialized["excluders"] = list(serialized["excluders"]) + [
            SquashingExcluder(axes=axesToMove)
        ]
        new_generator = CompoundGenerator.from_dict(serialized)
        return ParameterTweakInfo("generator", new_generator)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(UnrollingPart, self).setup(registrar)
        # Hooks
        registrar.hook(ValidateHook, self.validate)
