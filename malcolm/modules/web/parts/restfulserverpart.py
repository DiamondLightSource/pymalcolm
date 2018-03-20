from annotypes import Anno, add_call_types
from tornado.web import RequestHandler, asynchronous

from malcolm.core import Part, json_decode, json_encode, Get, Post, Return, \
    Error
from malcolm.modules import builtin
from ..hooks import ReportHandlersHook, ALoop, UHandlerInfos
from ..infos import HandlerInfo


# For some reason tornado doesn't make us implement all abstract methods
# noinspection PyAbstractClass
class RestfulHandler(RequestHandler):
    _server_part = None
    _loop = None

    def initialize(self, server_part=None, loop=None):
        self._server_part = server_part
        self._loop = loop

    @asynchronous
    def get(self, endpoint_str):
        # called from tornado thread
        path = endpoint_str.split("/")
        request = Get(path=path)
        request.set_callback(self.on_response)
        self._server_part.on_request(request)

    def on_response(self, response):
        # called from any thread
        self._loop.add_callback(self._on_response, response)

    def _on_response(self, response):
        # called from tornado thread
        if isinstance(response, Return):
            message = json_encode(response.value)
            self.finish(message + "\n")
        else:
            if isinstance(response, Error):
                message = response.message
            else:
                message = "Unknown response %s" % type(response)
            self.set_status(500, message)
            self.write_error(500)

    # curl --data 'parameters={"name": "me"}' \
    #     http://localhost:8080/blocks/hello/say_hello
    @asynchronous
    def post(self, endpoint_str):
        # called from tornado thread
        path = endpoint_str.split("/")
        parameters = json_decode(self.get_body_argument("parameters"))
        request = Post(path=path, parameters=parameters)
        request.set_callback(self.on_response)
        self._server_part.on_request(request)


with Anno("Part name and subdomain name to respond to queries on"):
    AName = str


class RestfulServerPart(Part):
    def __init__(self, name="rest"):
        # type: (AName) -> None
        super(RestfulServerPart, self).__init__(name)
        # Hooks
        self.register_hooked(ReportHandlersHook, self.report_handlers)

    @add_call_types
    def report_handlers(self, loop):
        # type: (ALoop) -> UHandlerInfos
        regexp = r"/%s/(.*)" % self.name
        info = HandlerInfo(
            regexp, RestfulHandler, server_part=self, loop=loop)
        return info

    def on_request(self, request):
        # called from tornado thread
        mri = request.path[0]
        self.registrar.report(builtin.infos.RequestInfo(request, mri))
