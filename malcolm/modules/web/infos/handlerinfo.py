from malcolm.core import Info


class HandlerInfo(Info):
    """Tornado RequestHandlers that should make up the webserver application

    Args:
        regex (str): Path for this handler to get requests from. E.g. r"/ws"
        request_class (tornado.web.RequestHandler): Request handler to
            instantiate for this
        **kwargs: Keyword args to be passed to request_class constructor
    """
    def __init__(self, regexp, request_class, **kwargs):
        self.regexp = regexp
        self.request_class = request_class
        self.kwargs = kwargs
