from annotypes import Anno, TYPE_CHECKING, Array, Sequence, Union
from enum import Enum

from malcolm.core import Future, Context, PartRegistrar, DEFAULT_TIMEOUT, Table
from malcolm.modules import scanning

if TYPE_CHECKING:
    from typing import List, Any


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


class ADBaseActions(object):
    def __init__(self, mri):
        # type: (str) -> None
        self.mri = mri
        # When arrayCounter gets to here we are done
        self.done_when_reaches = 0
        # CompletedSteps = arrayCounter + self.uniqueid_offset
        self.uniqueid_offset = 0
        # A future that completes when detector start calls back
        self.start_future = None  # type: Future

    def setup_detector_async(self, context, completed_steps, steps_to_do,
                             **kwargs):
        # type: (Context, int, int, **Any) -> List[Future]
        context.unsubscribe_all()
        child = context.block_view(self.mri)
        if completed_steps == 0:
            # This is an initial configure, so reset arrayCounter to 0
            array_counter = 0
            self.done_when_reaches = steps_to_do
        else:
            # This is rewinding or setting up for another batch,
            # skip to a uniqueID that has not been produced yet
            array_counter = self.done_when_reaches
            self.done_when_reaches += steps_to_do
        self.uniqueid_offset = completed_steps - array_counter
        for k, v in dict(
                arrayCounter=array_counter,
                imageMode="Multiple",
                numImages=steps_to_do,
                arrayCallbacks=True).items():
            if k not in kwargs and k in child:
                kwargs[k] = v
        fs = child.put_attribute_values_async(kwargs)
        return fs

    def setup_detector(self, context, completed_steps, steps_to_do, **kwargs):
        # type: (Context, int, int, **Any) -> None
        fs = self.setup_detector_async(
            context, completed_steps, steps_to_do, **kwargs)
        context.wait_all_futures(fs)

    def arm_detector(self, context):
        # type: (Context) -> None
        child = context.block_view(self.mri)
        self.start_future = child.start_async()
        child.when_value_matches("acquiring", True, timeout=DEFAULT_TIMEOUT)

    def wait_for_detector(self, context, registrar):
        # type: (Context, PartRegistrar) -> None
        child = context.block_view(self.mri)
        child.arrayCounterReadback.subscribe_value(
            self.update_completed_steps, registrar)
        context.wait_all_futures(self.start_future)
        # Now wait to make sure any update_completed_steps come in. Give
        # it 5 seconds to timeout just in case there are any stray frames that
        # haven't made it through yet
        child.when_value_matches(
            "arrayCounterReadback", self.done_when_reaches,
            timeout=DEFAULT_TIMEOUT)

    def abort_detector(self, context):
        # type: (Context) -> None
        child = context.block_view(self.mri)
        child.stop()
        # Stop is a put to a busy record which returns immediately
        # The detector might take a while to actually stop so use the
        # acquiring pv (which is the same asyn parameter as the busy record
        # that stop() pokes) to check that it has finished
        child.when_value_matches("acquiring", False, timeout=DEFAULT_TIMEOUT)

    def update_completed_steps(self, value, registrar):
        # type: (int, PartRegistrar) -> None
        completed_steps = value + self.uniqueid_offset
        registrar.report(scanning.infos.RunProgressInfo(completed_steps))
