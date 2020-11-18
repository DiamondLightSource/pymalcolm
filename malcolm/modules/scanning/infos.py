from enum import Enum
from typing import Any, Dict, List

from malcolm.core import Info, VMeta


class DatasetType(Enum):
    """NeXus type of a produced dataset"""

    #: Detector data, like the 2D data from an imaging detector
    PRIMARY = "primary"
    #: Calculated from detector data, like the sum of each frame
    SECONDARY = "secondary"
    #: Data that only makes sense when considered with detector data, like a
    #: measure of beam current with an ion chamber
    MONITOR = "monitor"
    #: The demand positions of an axis as specified by the generator
    POSITION_SET = "position_set"
    #: The readback positions of an axis that moves during the scan
    POSITION_VALUE = "position_value"
    #: The minimum value of the readback position of an axis in each frame
    POSITION_MIN = "position_min"
    #: The maximum value of the readback position of an axis in each frame
    POSITION_MAX = "position_max"


class ParameterTweakInfo(Info):
    """Info about a configure() parameter that needs to be tweaked

    Args:
        parameter: Parameter name, e.g. "generator"
        value: The value it should be changed to
    """

    def __init__(self, parameter: str, value: Any) -> None:
        self.parameter = parameter
        self.value = value


class ConfigureParamsInfo(Info):
    """Info about the parameters that should be passed to the Part in configure.
    The Controller will validate these when Block.configure() is called, and
    pass them to all Parts that have registered interest in them.

    Args:
        metas: Metas for the extra parameters
        required: List of required parameters
        defaults: Default values for parameters
    """

    def __init__(
        self, metas: Dict[str, VMeta], required: List[str], defaults: Dict[str, Any]
    ) -> None:
        self.metas = metas
        self.required = required
        self.defaults = defaults


class RunProgressInfo(Info):
    """Info about how far the current run has progressed

    Args:
        steps: The number of completed steps
    """

    def __init__(self, steps: int) -> None:
        self.steps = steps


class MinTurnaroundInfo(Info):
    """Info about the minimum time gap that should be left between points
    that are not joined together

    Args:
        gap: The minimum time gap in seconds
        interval: the minimum interval between two turnaround points
    """

    def __init__(self, gap: float, interval: float) -> None:
        self.gap = gap
        self.interval = interval


class DatasetProducedInfo(Info):
    """Declare that we will write the following dataset to file

    Args:
        name: Dataset name
        filename: Filename relative to the fileDir we were given
        type: What NeXuS dataset type it produces
        rank: The rank of the dataset including generator dims
        path: The path of the dataset within the file
        uniqueid: The path of the UniqueID dataset within the file
    """

    def __init__(
        self,
        name: str,
        filename: str,
        type: DatasetType,
        rank: int,
        path: str,
        uniqueid: str,
    ) -> None:
        self.name = name
        self.filename = filename
        self.type = type
        self.rank = rank
        self.path = path
        self.uniqueid = uniqueid


class MotionTrigger(Enum):
    """Request from a trigger source to the motion controller of what triggers
    it needs"""

    NONE = 0  #: No Triggers required
    ROW_GATE = 1  #: Trigger that spans each continuous joined section
    EVERY_POINT = 2  #: One trigger for each point


class MotionTriggerInfo(Info):
    """Declare that we need triggers of a certain sort from the motor controller

    Args:
        trigger: What type is required
    """

    def __init__(self, trigger: MotionTrigger) -> None:
        self.trigger = trigger


class DetectorMutiframeInfo(Info):
    """Declare that we are able to produce mutiple frames per point for this
    detector

    Args:
        mri: The mri of the detector in the DetectorTable
    """

    def __init__(self, mri: str) -> None:
        self.mri = mri


class ExposureDeadtimeInfo(Info):
    """Detector exposure time should be generator.duration - deadtime

    Args:
        readout_time: The per frame readout time of the detector
        frequency_accuracy: The crystal accuracy in ppm
        min_exposure: The minimum exposure time this detector supports
    """

    def __init__(
        self, readout_time: float, frequency_accuracy: float, min_exposure: float
    ) -> None:
        self.readout_time = readout_time
        self.frequency_accuracy = frequency_accuracy
        self.min_exposure = min_exposure

    def calculate_exposure(self, duration: float, exposure: float = 0.0) -> float:
        """Calculate the exposure to set the detector to given the duration of
        the frame and the readout_time and frequency_accuracy"""
        assert duration > 0, (
            "Duration %s for generator must be >0 to signify constant "
            "exposure" % duration
        )
        max_exposure = (
            duration
            - self.readout_time
            - (self.frequency_accuracy * duration / 1000000.0)
        )
        # If exposure time is 0, then use the max_exposure for this duration
        if exposure <= 0.0 or exposure > max_exposure:
            exposure = max_exposure
        elif exposure < self.min_exposure:
            exposure = self.min_exposure
        return exposure
