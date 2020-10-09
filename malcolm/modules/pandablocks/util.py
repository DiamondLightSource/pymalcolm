import os
from enum import Enum
from typing import Sequence, Union

from annotypes import Anno, Array

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
    ABitNames = Union[Array[str]]
UBitNames = Union[ABitNames, Sequence[str]]
with Anno("Current value for the Bit"):
    ABitValues = Union[Array[bool]]
UBitValues = Union[ABitValues, Sequence[bool]]
with Anno("Request this field is captured in PCAP"):
    ABitCaptures = Union[Array[bool]]
UBitCaptures = Union[ABitCaptures, Sequence[bool]]


class BitsTable(Table):
    def __init__(
        self, name: UBitNames, value: UBitValues, capture: UBitCaptures
    ) -> None:
        self.name = ABitNames(name)
        self.value = ABitValues(value)
        self.capture = ABitCaptures(capture)


class PositionCapture(Enum):
    """What to capture, if anything, with PCAP"""

    # In Python2 we have to define the order of members in an enum
    _order_ = "NO VALUE DIFF SUM MEAN MIN MAX MIN_MAX MIN_MAX_MEAN"

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
    APositionNames = Union[Array[str]]
UPositionNames = Union[APositionNames, Sequence[str]]
with Anno("Current scaled value for the Position"):
    APositionValues = Union[Array[float]]
UPositionValues = Union[APositionValues, Sequence[float]]
with Anno("Units for the scaled value of the Position"):
    APositionUnits = Union[Array[str]]
UPositionUnits = Union[APositionUnits, Sequence[str]]
with Anno("Scale factor to calculate scaled value of the Position"):
    APositionScales = Union[Array[float]]
UPositionScales = Union[APositionScales, Sequence[float]]
with Anno("Offset to calculate scaled value of the Position"):
    APositionOffsets = Union[Array[float]]
UPositionOffsets = Union[APositionOffsets, Sequence[float]]
with Anno("Whether and what to capture with PCAP"):
    APositionCaptures = Union[Array[PositionCapture]]
UPositionCaptures = Union[APositionCaptures, Sequence[PositionCapture]]


class PositionsTable(Table):
    def __init__(
        self,
        name: UPositionNames,
        value: UPositionValues,
        units: UPositionUnits,
        scale: UPositionScales,
        offset: UPositionOffsets,
        capture: UPositionCaptures,
    ) -> None:
        self.name = APositionNames(name)
        self.value = APositionValues(value)
        self.units = APositionUnits(units)
        self.scale = APositionScales(scale)
        self.offset = APositionOffsets(offset)
        self.capture = APositionCaptures(capture)
