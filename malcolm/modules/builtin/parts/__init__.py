# Expose a nice namespace
from malcolm.core import submodule_all

from .blockpart import (
    AConfig,
    AGroup,
    AMetaDescription,
    APartName,
    AWidget,
    AWriteable,
    BlockPart,
)
from .childpart import AInitialVisibility, AMri, APartName, AStateful, ChildPart
from .choicepart import (
    AConfig,
    AGroup,
    AMetaDescription,
    APartName,
    AWidget,
    AWriteable,
    ChoicePart,
)
from .float64part import (
    AConfig,
    AGroup,
    ALimitHigh,
    ALimitLow,
    AMetaDescription,
    APartName,
    APrecision,
    AUnits,
    AWidget,
    AWriteable,
    Float64Part,
)
from .grouppart import AMetaDescription, APartName, GroupPart
from .helppart import AHelpUrl, APartName, HelpPart
from .iconpart import ASvg, IconPart
from .labelpart import ALabelValue, LabelPart
from .stringpart import (
    AConfig,
    AGroup,
    AMetaDescription,
    APartName,
    AValue,
    AWidget,
    AWriteable,
    StringPart,
)

__all__ = submodule_all(globals())
