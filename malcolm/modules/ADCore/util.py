from annotypes import Anno, Array, Sequence, Union
from enum import Enum

from malcolm.core import Table


# If things don't get new frames in this time (seconds), consider them
# stalled and raise
FRAME_TIMEOUT = 60


class AttributeDatasetType(Enum):
    """Used to signal from a detector driver that it is producing an NDAttribute
    that should be published to the user, and what its NeXus type is"""
    #: Primary data that is directly relevant to the user, like a transmission
    #: diode.
    DETECTOR = "detector"
    #: Data that only makes sense when considered with detector data, like a
    #: measure of beam current with an ion chamber
    MONITOR = "monitor"
    #: Readback position of a motor that is taking part in the experiment
    POSITION = "position"


class DataType(Enum):
    """The datatype that should be used for the NDAttribute"""
    INT = "INT"  #: int32
    DOUBLE = "DOUBLE"  #: float64
    STRING = "STRING"  #: string
    DBRNATIVE = "DBR_NATIVE"  #: Whatever native type the PV has


class SourceType(Enum):
    """Where to get the NDAttribute data from"""
    PARAM = "paramAttribute"  #: From an asyn parameter of this driver
    PV = "PVAttribute"  #: From a PV name


class StatisticsName(Enum):
    """The types of statistics calculated by the areaDetector NDPluginStats"""
    MIN = "MIN_VALUE"  #: Minimum counts in any element
    MIN_X = "MIN_X"  #: X position of minimum counts
    MIN_Y = "MIN_Y"  #: Y position of minimum counts
    MAX = "MAX_VALUE"  #: Maximum counts in any element
    MAX_X = "MAX_X"  #: X position of maximum counts
    MAX_Y = "MAX_Y"  #: Y position of maximum counts
    MEAN = "MEAN_VALUE"  #: Mean counts of all elements
    SIGMA = "SIGMA_VALUE"  #: Sigma of all elements
    SUM = "TOTAL"  #: Sum of all elements
    NET = "NET"  #: Sum of all elements not in background region


with Anno("Is the IOC this part connects to running on Windows?"):
    APartRunsOnWindows = bool

with Anno("NDAttribute name to be exported"):
    AAttributeNames = Array[str]
with Anno("source ID for attribute (PV name for PVAttribute," +
          "asyn param name for paramAttribute)"):
    ASourceIds = Array[str]
with Anno("PV descriptions"):
    ADescriptions = Array[str]
with Anno("Types of attribute dataset"):
    AAttributeTypes = Array[AttributeDatasetType]
with Anno("Type of attribute source"):
    ASourceTypes = Array[SourceType]
with Anno("Type of attribute data"):
    ADataTypes = Array[DataType]
UAttributeNames = Union[AAttributeNames, Sequence[str]]
USourceIds = Union[ASourceIds, Sequence[str]]
UDescriptions = Union[ADescriptions, Sequence[str]]
UAttributeTypes = Union[AAttributeTypes, Sequence[AttributeDatasetType]]
UDataTypes = Union[ADataTypes, Sequence[DataType]]
USourceTypes = Union[ASourceTypes, Sequence[SourceType]]


class ExtraAttributesTable(Table):
    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    def __init__(self,
                 name,  # type: UAttributeNames
                 sourceId,  # type: USourceIds
                 description,  # type: UDescriptions
                 sourceType,  # type: USourceTypes
                 dataType,  # type: UDataTypes
                 datasetType,  # type: UAttributeTypes
                 ):
        # type: (...) -> None
        self.name = AAttributeNames(name)
        self.sourceId = ASourceIds(sourceId)
        self.description = ADescriptions(description)
        self.sourceType = ASourceTypes(sourceType)
        self.dataType = ADataTypes(dataType)
        self.datasetType = AAttributeTypes(datasetType)
