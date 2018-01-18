from annotypes import TYPE_CHECKING

from malcolm.core import Info
from .util import ConfigureParams

if TYPE_CHECKING:
    from typing import Type, Any


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
    """Info about the ConfigureParam that should be passed to the Part in
    configure(). Otherwise a ConfigureParam instance will be used

    Args:
        params: The ConfigureParams subclass to use
    """
    def __init__(self, params):
        # type: (Type[ConfigureParams]) -> None
        self.params = params


class RunProgressInfo(Info):
    """Info about how far the current run has progressed

    Args:
        steps: The number of completed steps
    """
    def __init__(self, steps):
        # type: (int) -> None
        self.steps = steps
