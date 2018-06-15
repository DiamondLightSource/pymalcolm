from annotypes import Anno, add_call_types
from tornado.websocket import WebSocketHandler, WebSocketError

from malcolm.core import Part, json_decode, deserialize_object, Request, PathRequest,\
    json_encode, Subscribe, Unsubscribe, Delta, Update, Error, Response, FieldError
from malcolm.modules import builtin
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
        msg_id = -1
        try:
            d = json_decode(message)

            try:
                msg_id = d['id']
            except KeyError:
                raise FieldError('id field not present in JSON message')

            request = deserialize_object(d, Request)
            request.set_callback(self.on_response)
            self._server_part.on_request(request)

        except Exception as e:
            self._server_part.log.exception("Error handling message from client")
            error = Error(msg_id, e)
            error_message = error.to_dict()
            self.write_message(json_encode(error_message))

    def on_response(self, response):
        # called from any thread
        self._loop.add_callback(
            self._server_part.on_response, response, self)

    # http://stackoverflow.com/q/24851207
    # TODO: remove this when the web gui is hosted from the box
    def check_origin(self, origin):
        return True


with Anno("Part name and subdomain name to host websocket on"):
    AName = str


class WebsocketServerPart(Part):
    def __init__(self, name="ws"):
        # type: (AName) -> None
        super(WebsocketServerPart, self).__init__(name)
        # {id: Subscribe}
        self._subscription_keys = {}
        # [mri]
        self._published = []
        # Hooks
        self.register_hooked(ReportHandlersHook, self.report_handlers)
        self.register_hooked(PublishHook, self.publish)

    @add_call_types
    def report_handlers(self, loop):
        # type: (ALoop) -> UHandlerInfos
        regexp = r"/%s" % self.name
        info = HandlerInfo(
            regexp, MalcWebSocketHandler, server_part=self, loop=loop)
        return info

    @add_call_types
    def publish(self, published):
        # type: (APublished) -> None
        # called from any thread
        self._published = published
        for request in self._subscription_keys.values():
            if request.path[0] == ".":
                self._notify_published(request)

    def on_request(self, request):
        # type: (Request) -> None
        # called from tornado thread
        if isinstance(request, PathRequest):
            if not request.path:
                raise ValueError("No path supplied")
        self.log.info("Request: %s", request)
        if isinstance(request, Subscribe):
            if request.generate_key() in self._subscription_keys.keys():
                raise FieldError("duplicate subscription ID on client")
            if request.path[0] == ".":
                # special entries
                assert len(request.path) == 2 and request.path[1] == "blocks", \
                    "Don't know how to subscribe to %s" % (request.path,)
                self._notify_published(request)
            self._subscription_keys[request.generate_key()] = request
            if request.path[0] == ".":
                return

        if isinstance(request, Unsubscribe):
            subscribe = self._subscription_keys.pop(request.generate_key())
            mri = subscribe.path[0]
            if mri == ".":
                # service requests on ourself
                response, cb = subscribe.return_response()
                cb(response)
                return
        else:
            mri = request.path[0]
        self.registrar.report(builtin.infos.RequestInfo(request, mri))

    def on_response(self, response, websocket):
        # type: (Response, MalcWebSocketHandler) -> None
        # called from tornado thread
        message = json_encode(response)
        try:
            websocket.write_message(message)
        except WebSocketError:
            # The websocket is dead. If the response was a Delta or Update, then
            # unsubscribe so the local controller doesn't keep on trying to
            # respond
            if isinstance(response, (Delta, Update)):
                # Websocket is dead so we can clear the subscription key.
                # Subsequent updates may come in before the unsubscribe, but
                # ignore them as we can't do anything about it
                subscribe = self._subscription_keys.pop(
                    (websocket.on_response, response.id), None)
                if subscribe:
                    self.log.info(
                        'WebSocket Error; unsubscribing from stale handle')
                    unsubscribe = Unsubscribe(response.id)
                    unsubscribe.set_callback(websocket.on_response)
                    self.registrar.report(builtin.infos.RequestInfo(
                        unsubscribe, subscribe.path[0]))

    def _notify_published(self, request):
        # type: (Subscribe) -> None
        # called from any thread
        if request.delta:
            cb, response = request.delta_response([[[], self._published]])
        else:
            cb, response = request.update_response(self._published)
        cb(response)
