from malcolm.core import Future, Block, PartRegistrar, Put, Request
from malcolm.modules import builtin, scanning
from malcolm.modules.pmac.parts import PmacChildPart

from annotypes import add_call_types, TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Dict, List

# 80 char line lengths...
AIV = builtin.parts.AInitialVisibility

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri

class BeamSelectorPart(PmacChildPart):

    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 initial_visibility=None  # type: AIV
                 ):
        # type: (...) -> None
        super(BeamSelectorPart, self).__init__(name, mri, initial_visibility)