from annotypes import Anno, add_call_types, TYPE_CHECKING

from malcolm.core import PartRegistrar
from malcolm.modules import builtin

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri
AIV = builtin.parts.AInitialVisibility

# TODO Type checking?
# TODO add call types

class BeamSelectorPart(builtin.parts.ChildPart):

    def __init__(self,
                 name, # type: APartName
                 mri, # type: AMri
                 initial_visibility = None # type: AIV
                 ):
        # type: (...) -> None

        pass

    def setup(self, registrar):
        # type: (PartRegistrar) -> None

        pass


