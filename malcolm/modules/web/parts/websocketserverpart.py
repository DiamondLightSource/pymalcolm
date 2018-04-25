from annotypes import Anno, add_call_types
from tornado.websocket import WebSocketHandler, WebSocketError

from malcolm.core import Part, json_decode, deserialize_object, Request, \
    json_encode, Subscribe, Unsubscribe, Delta, Update, Error
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
            try:
                d = json_decode(message)
            except Exception as e:
                raise Exception("Failed to decode JSON message: %s(%s)" % (type(e).__name__, str(e)))
            try:
                msg_id = d['id']
                request = deserialize_object(d, Request)
            except Exception as e:  # only thrown if no id and/or invalid or no typeid field
                raise Exception("Bad malcolm JSON message: %s(%s)" % (type(e).__name__, str(e)))
            try:
                request.set_callback(self.on_response)
                self._server_part.on_request(request)
            except Exception as e:
                raise Exception("Error handling request: %s(%s)" % (type(e).__name__, str(e)))

        except Exception as e:
            error = Error(msg_id, e)
            error_message = error.to_dict()
            self.write_message(error_message)

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
        # called from tornado thread
        self.log.info("Request: %s", request)
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
        self.registrar.report(builtin.infos.RequestInfo(request, mri))

    def on_response(self, response, write_message):
        # called from tornado thread
        message = json_encode(response)
        try:
            write_message(message)
        except WebSocketError:
            # The websocket is dead. If the response was a Delta or Update, then
            # unsubscribe so the local controller doesn't keep on trying to
            # respond
            if isinstance(response, (Delta, Update)):
                # Websocket is dead so we can clear the subscription key.
                # Subsequent updates may come in before the unsubscribe, but
                # ignore them as we can't do anything about it
                subscribe = self._subscription_keys.pop(response.id, None)
                if subscribe:
                    unsubscribe = Unsubscribe(subscribe.id)
                    unsubscribe.set_callback(subscribe.callback)
                    self.registrar.report(builtin.infos.RequestInfo(
                        unsubscribe, subscribe.path[0]))

    def _notify_published(self, request):
        # called from any thread
        cb, response = request.update_response(self._published)
        cb(response)
