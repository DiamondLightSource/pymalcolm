from annotypes import Anno, add_call_types, json_decode, json_encode
from tornado.web import RequestHandler, asynchronous

from malcolm.core import Part, Get, Post, Return, Error, PartRegistrar
from malcolm.modules import builtin
from ..hooks import ReportHandlersHook, UHandlerInfos
from ..infos import HandlerInfo
from ..util import IOLoopHelper


# For some reason tornado doesn't make us implement all abstract methods
# noinspection PyAbstractClass
class RestfulHandler(RequestHandler):
    _registrar = None

    def initialize(self, registrar=None):
        self._registrar = registrar  # type: PartRegistrar

    @asynchronous
    def get(self, endpoint_str):
        # called from tornado thread
        path = endpoint_str.split("/")
        request = Get(path=path)
        self.report_request(request)

    # curl --data 'parameters={"name": "me"}' \
    #     http://localhost:8008/blocks/hello/say_hello
    @asynchronous
    def post(self, endpoint_str):
        # called from tornado thread
        path = endpoint_str.split("/")
        parameters = json_decode(self.get_body_argument("parameters"))
        request = Post(path=path, parameters=parameters)
        self.report_request(request)

    def report_request(self, request):
        # called from tornado thread
        request.set_callback(self.on_response)
        mri = request.path[0]
        self._registrar.report(builtin.infos.RequestInfo(request, mri))

    def on_response(self, response):
        # called from cothread
        if isinstance(response, Return):
            message = json_encode(response.value)
            IOLoopHelper.call(self.finish, message + "\n")
        else:
            if isinstance(response, Error):
                message = response.message
            else:
                message = "Unknown response %s" % type(response)
            self.set_status(500, message)
            IOLoopHelper.call(self.write_error, 500)


with Anno("Part name and subdomain name to respond to queries on"):
    AName = str


class RestfulServerPart(Part):
    def __init__(self, name="rest"):
        # type: (AName) -> None
        super(RestfulServerPart, self).__init__(name)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(RestfulServerPart, self).setup(registrar)
        # Hooks
        registrar.hook(ReportHandlersHook, self.report_handlers)

    @add_call_types
    def report_handlers(self):
        # type: () -> UHandlerInfos
        regexp = r"/%s/(.*)" % self.name
        info = HandlerInfo(regexp, RestfulHandler, registrar=self.registrar)
        return info

