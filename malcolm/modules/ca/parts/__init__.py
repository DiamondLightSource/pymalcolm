# Expose a nice namespace
from malcolm.core import submodule_all

from .caactionpart import CAActionPart
from .cabooleanpart import CABooleanPart
from .cachararraypart import CACharArrayPart
from .cachoicepart import CAChoicePart
from .cadoublearraypart import CADoubleArrayPart
from .cadoublepart import CADoublePart
from .calongarraypart import CALongArrayPart
from .calongpart import CALongPart
from .castringpart import CAStringPart
from .cawaveformtablepart import CAWaveformTablePart

__all__ = submodule_all(globals())
