from annotypes import Anno, Array, Union, Sequence, TYPE_CHECKING
from enum import Enum
import numpy as np

from malcolm.core import Table, Future, Context, PartRegistrar, DEFAULT_TIMEOUT
from malcolm.modules import scanning

if TYPE_CHECKING:
    from typing import List, Any


class AttributeDatasetType(Enum):
    DETECTOR = "detector"
    MONITOR = "monitor"
    POSITION = "position"


class DatasetType(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MONITOR = "monitor"
    POSITION_SET = "position_set"
    POSITION_VALUE = "position_value"


class StatisticsName(Enum):
    MIN = "MIN_VALUE"  # Minimum counts in any element
    MIN_X = "MIN_X"  # X position of minimum counts
    MIN_Y = "MIN_Y"  # Y position of minimum counts
    MAX = "MAX_VALUE"  # Maximum counts in any element
    MAX_X = "MAX_X"  # X position of maximum counts
    MAX_Y = "MAX_Y"  # Y position of maximum counts
    MEAN = "MEAN_VALUE"  # Mean counts of all elements
    SIGMA = "SIGMA_VALUE"  # Sigma of all elements
    SUM = "TOTAL"  # Sum of all elements
    NET = "NET"  # Sum of all elements not in background region


with Anno("Dataset names"):
    ANameArray = Array[str]
with Anno("Filenames of HDF files relative to fileDir"):
    AFilenameArray = Array[str]
with Anno("Types of dataset"):
    ATypeArray = Array[DatasetType]
with Anno("Rank (number of dimensions) of the dataset"):
    ARankArray = Array[np.int32]
with Anno("Dataset paths within HDF files"):
    APathArray = Array[str]
with Anno("UniqueID array paths within HDF files"):
    AUniqueIDArray = Array[str]
UNameArray = Union[ANameArray, Sequence[str]]
UFilenameArray = Union[AFilenameArray, Sequence[str]]
UTypeArray = Union[ATypeArray, Sequence[DatasetType]]
URankArray = Union[ARankArray, Sequence[np.int32]]
UPathArray = Union[APathArray, Sequence[str]]
UUniqueIDArray = Union[AUniqueIDArray, Sequence[str]]


class DatasetTable(Table):
    # This will be serialized so we need type to be called that
    # noinspection PyShadowingBuiltins
    def __init__(self,
                 name,  # type: UNameArray
                 filename,  # type: UFilenameArray
                 type,  # type: UTypeArray
                 rank,  # type: URankArray
                 path,  # type: UPathArray
                 uniqueid,  # type: UUniqueIDArray
                 ):
        # type: (...) -> None
        self.name = ANameArray(name)
        self.filename = AFilenameArray(filename)
        self.type = ATypeArray(type)
        self.rank = ARankArray(rank)
        self.path = APathArray(path)
        self.uniqueid = AUniqueIDArray(uniqueid)


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
        self.start_future = context.block_view(self.mri).start_async()

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
