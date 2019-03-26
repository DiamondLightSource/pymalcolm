from annotypes import TYPE_CHECKING

from malcolm.core import Info, VMeta

if TYPE_CHECKING:
    from typing import Any, Dict, List


class ParameterTweakInfo(Info):
    # type: (str, Any) -> None
    """Info about a configure() parameter that needs to be tweaked

    Args:
        parameter: Parameter name, e.g. "generator"
        value: The value it should be changed to
    """
    def __init__(self, parameter, value):
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
    def __init__(self, metas, required, defaults):
        # type: (Dict[str, VMeta], List[str], Dict[str, Any]) -> None
        self.metas = metas
        self.required = required
        self.defaults = defaults


class RunProgressInfo(Info):
    """Info about how far the current run has progressed

    Args:
        steps: The number of completed steps
    """
    def __init__(self, steps):
        # type: (int) -> None
        self.steps = steps


class MinTurnaroundInfo(Info):
    """Info about the minimum time gap that should be left between points
    that are not joined together

    Args:
        gap: The minimum time gap in seconds
    """
    def __init__(self, gap):
        # type: (float) -> None
        self.gap = gap


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
    def __init__(self, name, filename, type, rank, path, uniqueid):
        # type: (str, str, DatasetType, int, str, str) -> None
        self.name = name
        self.filename = filename
        self.type = type
        self.rank = rank
        self.path = path
        self.uniqueid = uniqueid
