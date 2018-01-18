from annotypes import Mapping, Sequence, Anno, Array, Union

from malcolm.modules.builtin.hooks import ControllerHook, APart, AContext
from .infos import ParameterTweakInfo, Info
from .util import ConfigureParams

with Anno("Configuration parameters passed in"):
    AConfigureParams = ConfigureParams
with Anno("The Infos returned from other Parts"):
    APartInfo = Mapping[str, Array[Info]]
with Anno("Infos about current Part status to be passed to other parts"):
    AInfos = Array[Info]
with Anno("Parameters that need to be changed to make them compatible"):
    AParameterTweakInfos = Array[ParameterTweakInfo]
UInfos = Union[AInfos, Sequence[Info], Info, None]
UParameterTweakInfos = Union[AParameterTweakInfos, Sequence[ParameterTweakInfo],
                             ParameterTweakInfo, None]


class ValidateHook(ControllerHook[UParameterTweakInfos]):
    """Called at validate() to check parameters are valid"""

    def __init__(self, part, context, part_info, params):
        # type: (APart, AContext, APartInfo, AConfigureParams) -> None
        super(ValidateHook, self).__init__(**locals())

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


class ConfigureHook(ControllerHook[UInfos]):
    """Called at configure() to configure child block for a run"""

    def __init__(self,
                 part,  # type: APart
                 context,  # type: AContext
                 completed_steps,  # type: ACompletedSteps
                 steps_to_do,  # type: AStepsToDo
                 part_info,  # type: APartInfo
                 params,  # type: AConfigureParams
                 ):
        # type: (...) -> None
        super(ConfigureHook, self).__init__(**locals())

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
        super(PostConfigureHook, self).__init__(**locals())


class RunHook(ControllerHook[None]):
    """Called at run() to start the configured steps running"""


class PostRunArmedHook(ControllerHook[None]):
    """Called at the end of run() when there are more steps to be run"""

    def __init__(self,
                 part,  # type: APart
                 context,  # type: AContext
                 completed_steps,  # type: ACompletedSteps
                 steps_to_do,  # type: AStepsToDo
                 part_info,  # type: APartInfo
                 params,  # type: AConfigureParams
                 ):
        # type: (...) -> None
        super(PostRunArmedHook, self).__init__(**locals())


class PostRunReadyHook(ControllerHook[None]):
    """Called at the end of run() when there are no more steps to be run"""


class PauseHook(ControllerHook[None]):
    """Called at pause() to pause the current scan before Seek is called"""


class SeekHook(ControllerHook[None]):
    """Called at seek() or at the end of pause() to reconfigure for a different
    number of completed_steps"""

    def __init__(self,
                 part,  # type: APart
                 context,  # type: AContext
                 completed_steps,  # type: ACompletedSteps
                 steps_to_do,  # type: AStepsToDo
                 part_info,  # type: APartInfo
                 params,  # type: AConfigureParams
                 ):
        # type: (...) -> None
        super(SeekHook, self).__init__(**locals())


class ResumeHook(ControllerHook[None]):
    """Called at resume() to continue a paused scan"""


class AbortHook(ControllerHook[None]):
    """Called at abort() to stop the current scan"""
