from malcolm.core import PART_NAME_RE, Info
from malcolm.modules import scanning

from .util import AttributeDatasetType


class FilePathTranslatorInfo(Info):
    """Translate linux filepath to windows equivalent

    Args:
        windows_drive_letter: The drive letter assigned to the windows mount
        path_prefix: The location of the mount in linux (i.e. /dls or /dls_sw)
        network_drive: The network drive prefix on Windows (e.g. //dc). If the
        windows drive letter is an empty string, the network drive is prepended.
    """

    def __init__(self, windows_drive_letter, path_prefix, network_prefix):
        self.windows_drive_letter = windows_drive_letter
        self.path_prefix = path_prefix
        self.network_prefix = network_prefix

    @classmethod
    def translate_filepath(cls, part_info, filepath):
        translator = cls.filter_single_value(
            part_info,
            "No or multiple FilePathTranslatorPart found: must have exactly "
            "1 if any part in the AD chain is running on Windows",
        )
        assert filepath.startswith(
            translator.path_prefix
        ), "filepath %s does not start with expected prefix %s" % (
            filepath,
            translator.path_prefix,
        )
        assert (
            filepath.find(":") == -1
        ), "filepath %s has unexpected colon (incompatible on Windows)" % (filepath)

        if translator.network_prefix != "":
            win_path = filepath.replace(
                translator.path_prefix,
                translator.network_prefix + translator.path_prefix,
            ).replace("/", "\\")
        else:
            win_path = filepath.replace(
                translator.path_prefix, translator.windows_drive_letter + ":"
            ).replace("/", "\\")
        return win_path


class NDArrayDatasetInfo(Info):
    """Declare the NDArray data this produces as being a useful dataset to store
    to file

    Args:
        rank: The rank of the dataset, e.g. 2 for a 2D detector
    """

    def __init__(self, rank: int) -> None:
        self.rank = rank


class CalculatedNDAttributeDatasetInfo(Info):
    """Declare that we have calculated some statistics from the main dataset
    and these will be available

    Args:
        name: Dataset name that should be written to
        attr: NDAttribute name to get data from
    """

    def __init__(self, name: str, attr: str) -> None:
        self.name = name
        self.attr = attr


class NDAttributeDatasetInfo(Info):
    """Declare an NDAttribute attached to this NDArray to produce a useful
    dataset to store to file

    Args:
        name: Dataset name that should be written to, e.g. "I0.value"
        type: What NeXuS dataset type it produces, e.g. DatasetType.PRIMARY
        attr: NDAttribute name to get data from, e.g. "COUNTER1.Diff"
    """

    def __init__(self, name: str, type: scanning.infos.DatasetType, attr: str) -> None:
        self.name = name
        self.type = type
        self.attr = attr

    @classmethod
    def from_attribute_type(
        cls, name: str, type: AttributeDatasetType, attr: str
    ) -> "NDAttributeDatasetInfo":
        """Make an Info from the AttributeDatasetType

        Args:
            name: Dataset name without dots, e.g. "I0"
            type: What type it is, e.g. AttributeDatasetType.DETECTOR
            attr: NDAttribute name to get data from, e.g. "COUNTER1.Diff
        """
        assert PART_NAME_RE.match(name), (
            "Expected Alphanumeric dataset name (dash and underscore allowed)"
            + " got %r" % name
        )
        if type is AttributeDatasetType.DETECTOR:
            # Something like I0
            name = "%s.data" % name
            dtype = scanning.util.DatasetType.PRIMARY
        elif type is AttributeDatasetType.MONITOR:
            # Something like Iref
            name = "%s.data" % name
            dtype = scanning.util.DatasetType.MONITOR
        elif type is AttributeDatasetType.POSITION:
            # Something like x
            name = "%s.value" % name
            dtype = scanning.util.DatasetType.POSITION_VALUE
        else:
            raise AttributeError(
                "Bad dataset type %r, should be a %s" % (type, AttributeDatasetType)
            )
        return cls(name, dtype, attr)
