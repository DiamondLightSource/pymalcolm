from annotypes import Anno, Array, Sequence, Union
from tornado.ioloop import IOLoop

from malcolm.core import Hook, APublished
from malcolm.modules.builtin.hooks import APart
from .infos import HandlerInfo

with Anno("The IO loop that the server is running under"):
    ALoop = IOLoop
with Anno("Any handlers and regexps that should form part of tornado App"):
    AHandlerInfos = Array[HandlerInfo]
UHandlerInfos = Union[AHandlerInfos, Sequence[HandlerInfo], HandlerInfo, None]


class ReportHandlersHook(Hook):
    """Called at init() to get all the handlers that should make the application
    """
    def __init__(self, part, loop):
        # type: (APart, ALoop) -> None
        super(ReportHandlersHook, self).__init__(part, loop=loop)

    def validate_return(self, ret):
        # type: (UHandlerInfos) -> AHandlerInfos
        return AHandlerInfos(ret)


class PublishHook(Hook):
    """Called when a new block is added"""
    def __init__(self, part, published):
        # type: (APart, APublished) -> None
        super(PublishHook, self).__init__(part, published=published)
