from annotypes import Anno, Any, Array, Mapping, TYPE_CHECKING, NO_DEFAULT, \
    Sequence, Union

from scanpointgenerator import CompoundGenerator
from .infos import ParameterTweakInfo, Info

from malcolm.compat import OrderedDict
from malcolm.core import VMeta
from malcolm.modules import builtin
from .infos import ConfigureParamsInfo

if TYPE_CHECKING:
    from typing import Dict, Callable

with Anno("The Infos returned from other Parts"):
    APartInfo = Mapping[str, Array[Info]]
with Anno("Infos about current Part status to be passed to other parts"):
    AInfos = Array[Info]

with Anno("Generator instance providing specification for scan"):
    AGenerator = CompoundGenerator
with Anno("List of axes in inner dimension of generator that should be moved"):
    AAxesToMove = Array[str]
UAxesToMove = Union[AAxesToMove, Sequence[str]]
with Anno("Parameters that need to be changed to make them compatible"):
    AParameterTweakInfos = Array[ParameterTweakInfo]
UInfos = Union[AInfos, Sequence[Info], Info, None]
UParameterTweakInfos = Union[AParameterTweakInfos, Sequence[ParameterTweakInfo],
                             ParameterTweakInfo, None]
with Anno("Directory to write data to"):
    AFileDir = str
with Anno("Argument for fileTemplate, normally filename without extension"):
    AFormatName = str
with Anno("""Printf style template to generate filename relative to fileDir.
Arguments are:
  1) %s: the value of formatName"""):
    AFileTemplate = str
with Anno("The demand exposure time of this scan, 0 for the maximum possible"):
    AExposure = float

# Pull re-used annotypes into our namespace in case we are subclassed
APart = builtin.hooks.APart
AContext = builtin.hooks.AContext
# also bring in superclass which a subclasses may refer to
ControllerHook = builtin.hooks.ControllerHook


class ValidateHook(ControllerHook[UParameterTweakInfos]):
    """Called at validate() to check parameters are valid"""

    # Allow CamelCase for axesToMove as it must match ConfigureParams which
    # will become a configure argument, so must be camelCase to match EPICS
    # normative types conventions
    # noinspection PyPep8Naming
    def __init__(self,
                 part,  # type: APart
                 context,  # type: AContext
                 part_info,  # type: APartInfo
                 generator,  # type: AGenerator
                 axesToMove,  # type: AAxesToMove
                 **kwargs  # type: **Any
                 ):
        # type: (...) -> None
        super(ValidateHook, self).__init__(
            part, context, part_info=part_info, generator=generator,
            axesToMove=axesToMove, **kwargs)

    def validate_return(self, ret):
        # type: (UParameterTweakInfos) -> AParameterTweakInfos
        """Check that all returned infos are ParameterTweakInfo that list
        the parameters that need to be changed to make them compatible with
        this part. ValidateHook will be re-run with the modified parameters."""
        return AParameterTweakInfos(ret)


class ReportStatusHook(ControllerHook[UInfos]):
    """Called before Validate, Configure, PostRunArmed and Seek hooks to report
    the current configuration of all parts"""

    def validate_return(self, ret):
        # type: (UInfos) -> AInfos
        """Check that all parts return Info objects relevant to other parts"""
        return AInfos(ret)


with Anno("Number of steps already completed"):
    ACompletedSteps = int
with Anno("Number of steps we should configure for"):
    AStepsToDo = int


class PreConfigureHook(ControllerHook[None]):
    """Called before configure() to get the device into a suitable state to
    report status and run configure. Typically will load a saved design."""


class ConfigureHook(ControllerHook[UInfos]):
    """Called at configure() to configure child block for a run"""

    # Allow CamelCase for axesToMove as it must match ConfigureParams which
    # will become a configure argument, so must be camelCase to match EPICS
    # normative types conventions
    # noinspection PyPep8Naming
    def __init__(self,
                 part,  # type: APart
                 context,  # type: AContext
                 completed_steps,  # type: ACompletedSteps
                 steps_to_do,  # type: AStepsToDo
                 part_info,  # type: APartInfo
                 generator,  # type: AGenerator
                 axesToMove,  # type: AAxesToMove
                 **kwargs  # type: **Any
                 ):
        # type: (...) -> None
        super(ConfigureHook, self).__init__(
            part, context, completed_steps=completed_steps,
            steps_to_do=steps_to_do, part_info=part_info, generator=generator,
            axesToMove=axesToMove, **kwargs)

    @classmethod
    def create_info(cls, configure_func):
        # type: (Callable) -> ConfigureParamsInfo
        """Create a `ConfigureParamsInfo` describing the extra parameters
        that should be passed at configure"""
        call_types = getattr(configure_func, "call_types",
                             {})  # type: Dict[str, Anno]
        metas = OrderedDict()
        required = []
        defaults = OrderedDict()
        for k, anno in call_types.items():
            if k not in cls.call_types:
                scls = VMeta.lookup_annotype_converter(anno)
                metas[k] = scls.from_annotype(anno, writeable=True)
                if anno.default is NO_DEFAULT:
                    required.append(k)
                elif anno.default is not None:
                    defaults[k] = anno.default
        return ConfigureParamsInfo(metas, required, defaults)

    def validate_return(self, ret):
        # type: (UInfos) -> AInfos
        """Check that all parts return Info objects for storing as attributes
        """
        return AInfos(ret)


class PostConfigureHook(ControllerHook[None]):
    """Called at the end of configure() to store configuration info calculated
    in the Configure hook"""

    def __init__(self, part, context, part_info):
        # type: (APart, AContext, APartInfo) -> None
        super(PostConfigureHook, self).__init__(
            part, context, part_info=part_info)


class RunHook(ControllerHook[None]):
    """Called at run() to start the configured steps running"""


class PostRunArmedHook(ControllerHook[None]):
    """Called at the end of run() when there are more steps to be run"""

    # Allow CamelCase for axesToMove as it must match ConfigureParams which
    # will become a configure argument, so must be camelCase to match EPICS
    # normative types conventions
    # noinspection PyPep8Naming
    def __init__(self,
                 part,  # type: APart
                 context,  # type: AContext
                 completed_steps,  # type: ACompletedSteps
                 steps_to_do,  # type: AStepsToDo
                 part_info,  # type: APartInfo
                 generator,  # type: AGenerator
                 axesToMove,  # type: AAxesToMove
                 **kwargs  # type: **Any
                 ):
        # type: (...) -> None
        super(PostRunArmedHook, self).__init__(
            part, context, completed_steps=completed_steps,
            steps_to_do=steps_to_do, part_info=part_info, generator=generator,
            axesToMove=axesToMove, **kwargs)


class PostRunReadyHook(ControllerHook[None]):
    """Called at the end of run() when there are no more steps to be run"""


class PauseHook(ControllerHook[None]):
    """Called at pause() to pause the current scan before Seek is called"""


class SeekHook(ControllerHook[None]):
    """Called at seek() or at the end of pause() to reconfigure for a different
    number of completed_steps"""

    # Allow CamelCase for axesToMove as it must match ConfigureParams which
    # will become a configure argument, so must be camelCase to match EPICS
    # normative types conventions
    # noinspection PyPep8Naming
    def __init__(self,
                 part,  # type: APart
                 context,  # type: AContext
                 completed_steps,  # type: ACompletedSteps
                 steps_to_do,  # type: AStepsToDo
                 part_info,  # type: APartInfo
                 generator,  # type: AGenerator
                 axesToMove,  # type: AAxesToMove
                 **kwargs  # type: **Any
                 ):
        # type: (...) -> None
        super(SeekHook, self).__init__(
            part, context, completed_steps=completed_steps,
            steps_to_do=steps_to_do, part_info=part_info, generator=generator,
            axesToMove=axesToMove, **kwargs)


class ResumeHook(ControllerHook[None]):
    """Called at resume() to continue a paused scan"""


class AbortHook(ControllerHook[None]):
    """Called at abort() to stop the current scan"""
