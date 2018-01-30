from annotypes import Anno, add_call_types
from tornado.websocket import WebSocketHandler, WebSocketError

from malcolm.core import Hook, Part, json_decode, deserialize_object, \
    Request, json_encode, Subscribe, Unsubscribe, Delta, Update
from ..infos import HandlerInfo
from ..hooks import ReportHandlersHook, ALoop, UHandlerInfos, PublishHook, \
    APublished


# For some reason tornado doesn't make us implement all abstract methods
# noinspection PyAbstractClass
class MalcWebSocketHandler(WebSocketHandler):
    _server_part = None
    _loop = None

    def initialize(self, server_part=None, loop=None):
        self._server_part = server_part
        self._loop = loop

    def on_message(self, message):
        # called in tornado's thread
        d = json_decode(message)
        request = deserialize_object(d, Request)
        request.set_callback(self.on_response)
        self._server_part.on_request(request)

    def on_response(self, response):
        # called from any thread
        self._loop.add_callback(
            self._server_part.on_response, response, self.write_message)

    # http://stackoverflow.com/q/24851207
    # TODO: remove this when the web gui is hosted from the box
    def check_origin(self, origin):
        return True


with Anno("Part name and subdomain name to host websocket on"):
    AName = str


class WebsocketServerPart(Part):
    def __init__(self, name):
        # type: (AName) -> None
        super(WebsocketServerPart, self).__init__(name)
        # {id: Subscribe}
        self._subscription_keys = {}
        # [mri]
        self._published = []

    def on_hook(self, hook):
        # type: (Hook) -> None
        if isinstance(hook, ReportHandlersHook):
            hook(self.report_handlers)
        elif isinstance(hook, PublishHook):
            hook(self.publish)

    @add_call_types
    def report_handlers(self, loop):
        # type: (ALoop) -> UHandlerInfos
        regexp = r"/%s" % self.name
        info = HandlerInfo(
            regexp, MalcWebSocketHandler, server_part=self, loop=loop)
        return info

    @add_call_types
    def publish(self, publish):
        # type: (APublished) -> None
        # called from any thread
        self._published = publish
        for request in self._subscription_keys.values():
            if request.path[0] == ".":
                self._notify_published(request)

    def on_request(self, request):
        # called from tornado thread
        if isinstance(request, Subscribe):
            if request.path[0] == ".":
                # special entries
                assert request.path[1] == "blocks", \
                    "Don't know how to subscribe to %s" % (request.path,)
                self._notify_published(request)
            self._subscription_keys[request.id] = request
            if request.path[0] == ".":
                return

        if isinstance(request, Unsubscribe):
            subscribe = self._subscription_keys.pop(request.id)
            mri = subscribe.path[0]
            if mri == ".":
                # service requests on ourself
                response, cb = subscribe.return_response()
                cb(response)
                return
        else:
            mri = request.path[0]
        controller = self.process.get_controller(mri)
        controller.handle_request(request)

    def on_response(self, response, write_message):
        # called from tornado thread
        message = json_encode(response)
        try:
            write_message(message)
        except WebSocketError:
            if isinstance(response, (Delta, Update)):
                request = self._subscription_keys[response.id]
                unsubscribe = Unsubscribe(request.id)
                controller = self.process.get_controller(request.path[0])
                controller.handle_request(unsubscribe)

    def _notify_published(self, request):
        # called from any thread
        cb, response = request.update_response(self._published)
        cb(response)




