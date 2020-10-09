from annotypes import Anno, add_call_types, json_decode, json_encode
from tornado import gen
from tornado.queues import Queue
from tornado.web import RequestHandler

from malcolm.core import Error, Get, Part, PartRegistrar, Post, Return
from malcolm.modules import builtin

from ..hooks import ReportHandlersHook, UHandlerInfos
from ..infos import HandlerInfo
from ..util import IOLoopHelper


# For some reason tornado doesn't make us implement all abstract methods
# noinspection PyAbstractClass
class RestfulHandler(RequestHandler):
    _registrar = None
    _queue = None

    def initialize(self, registrar=None):
        self._registrar: PartRegistrar = registrar
        self._queue = Queue()

    @gen.coroutine
    def get(self, endpoint_str):
        # called from tornado thread
        path = endpoint_str.split("/")
        request = Get(path=path)
        self.report_request(request)
        response = yield self._queue.get()
        self.handle_response(response)

    # curl -d '{"name": "me"}' http://localhost:8008/rest/HELLO/greet
    @gen.coroutine
    def post(self, endpoint_str):
        # called from tornado thread
        path = endpoint_str.split("/")
        parameters = json_decode(self.request.body.decode())
        request = Post(path=path, parameters=parameters)
        self.report_request(request)
        response = yield self._queue.get()
        self.handle_response(response)

    def report_request(self, request):
        # called from tornado thread
        request.set_callback(self.queue_response)
        mri = request.path[0]
        self._registrar.report(builtin.infos.RequestInfo(request, mri))

    def queue_response(self, response):
        # called from cothread
        IOLoopHelper.call(self._queue.put, response)

    def handle_response(self, response):
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


with Anno("Part name and subdomain name to respond to queries on"):
    AName = str


class RestfulServerPart(Part):
    def __init__(self, name: AName = "rest") -> None:
        super().__init__(name)

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(ReportHandlersHook, self.on_report_handlers)

    @add_call_types
    def on_report_handlers(self) -> UHandlerInfos:
        regexp = r"/%s/(.*)" % self.name
        info = HandlerInfo(regexp, RestfulHandler, registrar=self.registrar)
        return info
