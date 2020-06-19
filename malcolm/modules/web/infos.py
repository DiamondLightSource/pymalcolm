from annotypes import TYPE_CHECKING
from tornado.web import RequestHandler

from malcolm.core import Info

if TYPE_CHECKING:
    from typing import Type, Any


class HandlerInfo(Info):
    """Tornado RequestHandlers that should make up the webserver application

    Args:
        regex: Path for this handler to get requests from. E.g. r"/ws"
        request_class: Request handler to instantiate for this
        **kwargs: Keyword args to be passed to request_class constructor
    """
    def __init__(self, regexp, request_class, **kwargs):
        # type: (str, Type[RequestHandler], **Any) -> None
        self.regexp = regexp
        self.request_class = request_class
        self.kwargs = kwargs
