import os

from annotypes import Anno, Array, Union, Sequence
from enum import Enum

from malcolm.core import Table
from .pandablocksclient import PandABlocksClient


with Anno("The Client to use to get and set data"):
    AClient = PandABlocksClient
with Anno("Documentation URL base to get HTML help pages from"):
    ADocUrlBase = str
with Anno("The name of the Block, like LUT1 or PCAP"):
    ABlockName = str

DOC_URL_BASE = "https://pandablocks-fpga.readthedocs.io/en/autogen"

# Where all the icon SVGs live
SVG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "icons"))


with Anno("Block and Field name for the Bit"):
    ABitNames = Array[str]
UBitNames = Union[ABitNames, Sequence[str]]
with Anno("Current value for the Bit"):
    ABitValues = Array[bool]
UBitValues = Union[ABitValues, Sequence[bool]]
with Anno("Request this field is captured in PCAP"):
    ABitCaptures = Array[bool]
UBitCaptures = Union[ABitCaptures, Sequence[bool]]


class BitsTable(Table):
    def __init__(self, name, value, capture):
        # type: (UBitNames, UBitValues, UBitCaptures) -> None
        self.name = ABitNames(name)
        self.value = ABitValues(value)
        self.capture = ABitCaptures(capture)


class PositionCapture(Enum):
    """What to capture, if anything, with PCAP"""

    NO = "No"
    VALUE = "Value"
    DIFF = "Diff"
    SUM = "Sum"
    MEAN = "Mean"
    MIN = "Min"
    MAX = "Max"
    MIN_MAX = "Min Max"
    MIN_MAX_MEAN = "Min Max Mean"


with Anno("Block and Field name for the Position"):
    APositionNames = Array[str]
UPositionNames = Union[APositionNames, Sequence[str]]
with Anno("Current scaled value for the Position"):
    APositionValues = Array[float]
UPositionValues = Union[APositionValues, Sequence[float]]
with Anno("Units for the scaled value of the Position"):
    APositionUnits = Array[str]
UPositionUnits = Union[APositionUnits, Sequence[str]]
with Anno("Scale factor to calculate scaled value of the Position"):
    APositionScales = Array[float]
UPositionScales = Union[APositionScales, Sequence[float]]
with Anno("Offset to calculate scaled value of the Position"):
    APositionOffsets = Array[float]
UPositionOffsets = Union[APositionOffsets, Sequence[float]]
with Anno("Whether and what to capture with PCAP"):
    APositionCaptures = Array[PositionCapture]
UPositionCaptures = Union[APositionCaptures, Sequence[PositionCapture]]


class PositionsTable(Table):
    def __init__(self,
                 name,  # type: UPositionNames
                 value,  # type: UPositionValues
                 units,  # type: UPositionUnits
                 scale,  # type: UPositionScales
                 offset,  # type: UPositionOffsets
                 capture,  # type: UPositionCaptures
                 ):
        # type: (...) -> None
        self.name = APositionNames(name)
        self.value = APositionValues(value)
        self.units = APositionUnits(units)
        self.scale = APositionScales(scale)
        self.offset = APositionOffsets(offset)
        self.capture = APositionCaptures(capture)
