""" scanning.utils provides shared utility functions and classes.
For consistency and to avoid circular dependencies, the following
rules are applied:
- All types required to initialize hook classes are in the hooks namespace
- All types required to initialize info classes are in the infos namespace
- util depends on hooks and infos (not vice versa)"""

from annotypes import Anno, Array, Union, Sequence, Any, Serializable
from scanpointgenerator import CompoundGenerator
import numpy as np

from malcolm.core import VMeta, NTUnion, Table, NumberMeta, Widget, \
    Display, AttributeModel
from malcolm.modules import builtin
from .infos import DatasetType

from .hooks import AGenerator, AAxesToMove, UAxesToMove


def exposure_attribute(min_exposure):
    # type: (float) -> AttributeModel
    meta = NumberMeta(
        "float64", "The calculated exposure for this run",
        tags=[Widget.TEXTUPDATE.tag()],
        display=Display(precision=6, units="s", limitLow=min_exposure)
    )
    return meta.create_attribute_model()


class ConfigureParams(Serializable):
    # This will be serialized, so maintain camelCase for axesToMove
    # noinspection PyPep8Naming
    def __init__(self, generator, axesToMove=None, **kwargs):
        # type: (AGenerator, UAxesToMove, **Any) -> None
        if kwargs:
            # Got some additional args to report
            self.call_types = ConfigureParams.call_types.copy()
            for k in kwargs:
                # We don't use this apart from its presence,
                # so no need to fill in description, typ, etc.
                self.call_types[k] = Anno("")
            self.__dict__.update(kwargs)
        self.generator = generator
        if axesToMove is None:
            axesToMove = generator.axes
        self.axesToMove = AAxesToMove(axesToMove)


@Serializable.register_subclass("malcolm:core/PointGeneratorMeta:1.0")
@VMeta.register_annotype_converter(CompoundGenerator)
class PointGeneratorMeta(VMeta):

    attribute_class = NTUnion

    def doc_type_string(self):
        return "CompoundGenerator"

    def default_widget(self):
        return Widget.TREE

    def validate(self, value):
        if value is None:
            return CompoundGenerator([], [], [])
        elif isinstance(value, CompoundGenerator):
            return value
        elif isinstance(value, dict):
            # Sanitise the dict in place
            # TODO: remove this when scanpoint generator supports ndarray inputs
            def sanitize(d):
                for k, v in d.items():
                    if isinstance(v, np.ndarray):
                        d[k] = list(v)
                    elif isinstance(v, list):
                        for x in v:
                            if isinstance(x, dict):
                                sanitize(x)
                    elif isinstance(v, dict):
                        sanitize(v)
            sanitize(value)
            return CompoundGenerator.from_dict(value)
        else:
            raise TypeError(
                "Value %s must be a Generator object or dictionary" % value)

with Anno("Dataset names"):
    ADatasetNames = Array[str]
with Anno("Filenames of HDF files relative to fileDir"):
    AFilenames = Array[str]
with Anno("Types of dataset"):
    ADatasetTypes = Array[DatasetType]
with Anno("Rank (number of dimensions) of the dataset"):
    ARanks = Array[np.int32]
with Anno("Dataset paths within HDF files"):
    APaths = Array[str]
with Anno("UniqueID array paths within HDF files"):
    AUniqueIDs = Array[str]
UDatasetNames = Union[ADatasetNames, Sequence[str]]
UFilenames = Union[AFilenames, Sequence[str]]
UDatasetTypes = Union[ADatasetTypes, Sequence[DatasetType]]
URanks = Union[ARanks, Sequence[np.int32]]
UPaths = Union[APaths, Sequence[str]]
UUniqueIDs = Union[AUniqueIDs, Sequence[str]]


class DatasetTable(Table):
    # This will be serialized so we need type to be called type
    # noinspection PyShadowingBuiltins
    def __init__(self,
                 name,  # type: UDatasetNames
                 filename,  # type: UFilenames
                 type,  # type: UDatasetTypes
                 rank,  # type: URanks
                 path,  # type: UPaths
                 uniqueid,  # type: UUniqueIDs
                 ):
        # type: (...) -> None
        self.name = ADatasetNames(name)
        self.filename = AFilenames(filename)
        self.type = ADatasetTypes(type)
        self.rank = ARanks(rank)
        self.path = APaths(path)
        self.uniqueid = AUniqueIDs(uniqueid)


with Anno("Detector names"):
    ADetectorNames = Array[str]
with Anno("Detector block mris"):
    ADetectorMris = Array[str]
with Anno("Exposure of each detector frame for the current scan"):
    AExposures = Array[float]
with Anno("Number of detector frames for each generator point"):
    AFramesPerStep = Array[np.int32]
UDetectorNames = Union[ADetectorNames, Sequence[str]]
UDetectorMris = Union[ADetectorMris, Sequence[str]]
UExposures = Union[AExposures, Sequence[float]]
UFramesPerStep = Union[AFramesPerStep, Sequence[np.int32]]


class DetectorTable(Table):
    # Will be serialized so use camelCase
    # noinspection PyPep8Naming
    def __init__(self,
                 name,  # type: UDetectorNames
                 mri,  # type: UDetectorMris
                 exposure,  # type: UExposures
                 framesPerStep,  # type: UFramesPerStep
                 ):
        # type: (...) -> None
        self.name = ADetectorNames(name)
        self.mri = ADetectorMris(mri)
        self.exposure = AExposures(exposure)
        self.framesPerStep = AFramesPerStep(framesPerStep)


class RunnableStates(builtin.util.ManagerStates):
    """This state set covers controllers and parts that can be configured and
    then run, and have the ability to pause and rewind"""

    CONFIGURING = "Configuring"
    ARMED = "Armed"
    RUNNING = "Running"
    POSTRUN = "PostRun"
    FINISHED = "Finished"
    PAUSED = "Paused"
    SEEKING = "Seeking"
    ABORTING = "Aborting"
    ABORTED = "Aborted"

    def create_block_transitions(self):
        super(RunnableStates, self).create_block_transitions()
        # Set transitions for normal states
        self.set_allowed(self.READY, self.CONFIGURING)
        self.set_allowed(self.CONFIGURING, self.ARMED)
        self.set_allowed(self.ARMED,
                         self.RUNNING, self.SEEKING, self.RESETTING)
        self.set_allowed(self.RUNNING, self.POSTRUN, self.SEEKING)
        self.set_allowed(self.POSTRUN, self.FINISHED, self.ARMED, self.SEEKING)
        self.set_allowed(self.FINISHED, self.SEEKING, self.RESETTING,
                         self.CONFIGURING)
        self.set_allowed(self.SEEKING, self.ARMED, self.PAUSED, self.FINISHED)
        self.set_allowed(self.PAUSED, self.SEEKING, self.RUNNING)

        # Add Abort to all normal states
        normal_states = [
            self.READY, self.CONFIGURING, self.ARMED, self.RUNNING,
            self.POSTRUN, self.PAUSED, self.SEEKING, self.FINISHED]
        for state in normal_states:
            self.set_allowed(state, self.ABORTING)

        # Set transitions for aborted states
        self.set_allowed(self.ABORTING, self.ABORTED)
        self.set_allowed(self.ABORTED, self.RESETTING)
