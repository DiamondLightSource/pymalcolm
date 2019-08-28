from malcolm.core import Info
from malcolm.modules import scanning
from .util import AttributeDatasetType


class FilePathTranslatorInfo(Info):
    """Translate linux filepath to windows equivalent

    Args:
        windows_drive_letter: The drive letter assigned to the windows mount
        path_prefix: The location of the mount in linux (i.e. /dls or /dls_sw)
    """

    def __init__(self, windows_drive_letter, path_prefix):
        self.windows_drive_letter = windows_drive_letter
        self.path_prefix = path_prefix

    @classmethod
    def translate_filepath(cls, part_info, filepath):
        translator = cls.filter_single_value(
            part_info,
            "No or multiple FilePathTranslatorPart found: must have exactly "
            "1 if any part in the AD chain is running on Windows")
        assert filepath.startswith(translator.path_prefix), \
            "filepath %s does not start with expected prefix %s" % (
                filepath, translator.path_prefix)
        return filepath.replace(
            translator.path_prefix,
            translator.windows_drive_letter + ":"
        ).replace("/", "\\")


class ExposureDeadtimeInfo(Info):
    """Detector exposure time should be generator.duration - deadtime

    Args:
        readout_time: The per frame readout time of the detector
        frequency_accuracy: The crystal accuracy in ppm
        min_exposure: The minimum exposure time this detector supports
    """
    def __init__(self, readout_time, frequency_accuracy, min_exposure):
        # type: (float, float, float) -> None
        self.readout_time = readout_time
        self.frequency_accuracy = frequency_accuracy
        self.min_exposure = min_exposure

    def calculate_exposure(self, duration, exposure=0.0):
        # type: (float) -> float
        """Calculate the exposure to set the detector to given the duration of
        the frame and the readout_time and frequency_accuracy"""
        assert duration > 0, \
            "Duration %s for generator must be >0 to signify constant " \
            "exposure" % duration
        max_exposure = duration - self.readout_time - (
                self.frequency_accuracy * duration / 1000000.0)
        # If exposure time is 0, then use the max_exposure for this duration
        if exposure <= 0.0:
            exposure = max_exposure
        assert self.min_exposure <= exposure <= max_exposure, \
            "Exposure %s should be in range %s to %s" % (
                self.min_exposure, exposure, max_exposure)
        return exposure


class NDArrayDatasetInfo(Info):
    """Declare the NDArray data this produces as being a useful dataset to store
    to file

    Args:
        rank: The rank of the dataset, e.g. 2 for a 2D detector
    """

    def __init__(self, rank):
        # type: (int) -> None
        self.rank = rank


class CalculatedNDAttributeDatasetInfo(Info):
    """Declare that we have calculated some statistics from the main dataset
    and these will be available

    Args:
        name: Dataset name that should be written to
        attr: NDAttribute name to get data from
    """

    def __init__(self, name, attr):
        # type: (str, str) -> None
        self.name = name
        self.attr = attr


class NDAttributeDatasetInfo(Info):
    """Declare an NDAttribute attached to this NDArray to produce a useful
    dataset to store to file

    Args:
        name: Dataset name that should be written to, like x.value or det.data
        type: What NeXuS dataset type it produces, like position_value
        attr: NDAttribute name to get data from
        rank: The rank of the dataset
    """

    def __init__(self, name, type, attr, rank):
        # type: (str, scanning.util.DatasetType, str, int) -> None
        self.name = name
        self.type = type
        self.attr = attr
        self.rank = rank

    @classmethod
    def from_attribute_type(cls, name, type, attr, rank):
        # type: (str, AttributeDatasetType, str, str) -> NDArrayDatasetInfo
        if type is AttributeDatasetType.DETECTOR:
            # Something like I0
            name = "%s.data" % name
            type = scanning.util.DatasetType.PRIMARY
        elif type is AttributeDatasetType.MONITOR:
            # Something like Iref
            name = "%s.data" % name
            type = scanning.util.DatasetType.MONITOR
        elif type is AttributeDatasetType.POSITION:
            # Something like x
            name = "%s.value" % name
            type = scanning.util.DatasetType.POSITION_VALUE
        else:
            raise TypeError("Bad AttributeDatasetType %s" % type)
        return cls(name, type, attr, rank)

