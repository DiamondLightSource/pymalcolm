from annotypes import Anno, Array, Sequence, Union

from malcolm.core import Hook
from malcolm.modules import builtin
from .infos import HandlerInfo

with Anno("Any handlers and regexps that should form part of tornado App"):
    AHandlerInfos = Array[HandlerInfo]
UHandlerInfos = Union[AHandlerInfos, Sequence[HandlerInfo], HandlerInfo, None]

# Pull re-used annotypes into our namespace in case we are subclassed
APart = builtin.hooks.APart


class ReportHandlersHook(Hook):
    """Called at init() to get all the handlers that should make the application
    """
    def __init__(self, part):
        # type: (APart) -> None
        super(ReportHandlersHook, self).__init__(part)

    def validate_return(self, ret):
        # type: (UHandlerInfos) -> AHandlerInfos
        return AHandlerInfos(ret)
