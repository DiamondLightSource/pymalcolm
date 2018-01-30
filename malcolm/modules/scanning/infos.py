from annotypes import TYPE_CHECKING, Anno, NO_DEFAULT

from malcolm.core import Info, VMeta
from malcolm.compat import OrderedDict

if TYPE_CHECKING:
    from typing import Any, Dict, List, Callable


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
    """Info about the parameters that should be passed to the Part in configure

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

    @classmethod
    def from_configure(cls, func):
        # type: (Callable) -> ConfigureParamsInfo
        call_types = getattr(func, "call_types", {})  # type: Dict[str, Anno]
        metas = OrderedDict()
        required = []
        defaults = OrderedDict()
        for k, anno in call_types.items():
            scls = VMeta.lookup_annotype_converter(anno)
            metas[k] = scls.from_annotype(anno, writeable=True)
            if anno.default is NO_DEFAULT:
                required.append(k)
            elif anno.default is not None:
                defaults[k] = anno.default
        return cls(metas, required, defaults)


class RunProgressInfo(Info):
    """Info about how far the current run has progressed

    Args:
        steps: The number of completed steps
    """
    def __init__(self, steps):
        # type: (int) -> None
        self.steps = steps
