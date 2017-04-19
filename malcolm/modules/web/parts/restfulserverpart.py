from tornado.web import RequestHandler, asynchronous

from malcolm.core import method_takes, Part, json_decode, json_encode, Get, \
    Post, Return, Error
from malcolm.modules.builtin.vmetas import StringMeta
from malcolm.modules.web.controllers import HTTPServerComms
from malcolm.modules.web.infos import HandlerInfo


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
        request = Get(path=path, callback=self.on_response)
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

    # curl --data 'parameters={"name": "me"}' http://localhost:8888/blocks/hello/say_hello
    @asynchronous
    def post(self, endpoint_str):
        # called from tornado thread
        path = endpoint_str.split("/")
        parameters = json_decode(self.get_body_argument("parameters"))
        request = Post(
            path=path, parameters=parameters, callback=self.on_response)
        self._server_part.on_request(request)


@method_takes(
    "name", StringMeta(
        "Name of the subdomain to respond to queries on"), "rest")
class RestfulServerPart(Part):
    def __init__(self, params):
        self.params = params
        super(RestfulServerPart, self).__init__(params.name)

    @HTTPServerComms.ReportHandlers
    def report_handlers(self, context, loop):
        regexp = r"/%s/(.*)" % self.params.name
        info = HandlerInfo(
            regexp, RestfulHandler, server_part=self, loop=loop)
        return [info]

    def on_request(self, request):
        # called from tornado thread
        controller = self.get_controller(request.path[0])
        controller.handle_request(request)
