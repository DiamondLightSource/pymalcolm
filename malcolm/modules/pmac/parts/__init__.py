# Expose a nice namespace
from malcolm.core import submodule_all

from .beamselectorpart import BeamSelectorPart
from .compoundmotorsinkportspart import (
    AGroup,
    APartName,
    ARbv,
    CompoundMotorSinkPortsPart,
)
from .cspart import AMri, CSPart
from .cssourceportspart import AGroup, APartName, ARbv, CSSourcePortsPart
from .motorpremovepart import AMri, APartName, MotorPreMovePart
from .pmacchildpart import AMri, APartName, PmacChildPart
from .pmacstatuspart import PmacStatusPart
from .pmactrajectorypart import AMri, APartName, PmacTrajectoryPart
from .rawmotorsinkportspart import AGroup, RawMotorSinkPortsPart

__all__ = submodule_all(globals())
