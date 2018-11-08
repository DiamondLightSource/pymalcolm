import logging

from annotypes import Anno, add_call_types, TYPE_CHECKING
from tornado.websocket import WebSocketHandler, WebSocketError

from malcolm.core import Part, json_decode, deserialize_object, Request, \
    json_encode, Subscribe, Unsubscribe, Delta, Update, Error, \
    Response, FieldError, PartRegistrar
from malcolm.modules import builtin
from ..infos import HandlerInfo
from ..hooks import ReportHandlersHook, UHandlerInfos
from ..util import IOLoopHelper


if TYPE_CHECKING:
    from typing import Dict

# Create a module level logger
log = logging.getLogger(__name__)


# For some reason tornado doesn't make us implement all abstract methods
# noinspection PyAbstractClass
class MalcWebSocketHandler(WebSocketHandler):
    _registrar = None
    _id_to_mri = None

    def initialize(self, registrar=None):
        self._registrar = registrar  # type: PartRegistrar
        # {id: mri}
        self._id_to_mri = {}  # type: Dict[int, str]

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
            if isinstance(request, Subscribe):
                assert msg_id not in self._id_to_mri, \
                    "Duplicate subscription ID %d" % msg_id
                self._id_to_mri[msg_id] = request.path[0]
            if isinstance(request, Unsubscribe):
                mri = self._id_to_mri[msg_id]
            else:
                mri = request.path[0]
            log.info("Request: %s", request)
            self._registrar.report(builtin.infos.RequestInfo(request, mri))
        except Exception as e:
            log.exception("Error handling message:\n%s", message)
            error = Error(msg_id, e)
            error_message = error.to_dict()
            self.write_message(json_encode(error_message))

    def on_response(self, response):
        # called from cothread
        IOLoopHelper.call(self._on_response, response)

    def _on_response(self, response):
        # type: (Response) -> None
        # called from tornado thread
        message = json_encode(response)
        try:
            self.write_message(message)
        except WebSocketError:
            # The websocket is dead. If the response was a Delta or Update, then
            # unsubscribe so the local controller doesn't keep on trying to
            # respond
            if isinstance(response, (Delta, Update)):
                # Websocket is dead so we can clear the subscription key.
                # Subsequent updates may come in before the unsubscribe, but
                # ignore them as we can't do anything about it
                mri = self._id_to_mri.pop(response.id, None)
                if mri:
                    log.info(
                        'WebSocket Error: unsubscribing from stale handle')
                    unsubscribe = Unsubscribe(response.id)
                    unsubscribe.set_callback(self.on_response)
                    self._registrar.report(
                        builtin.infos.RequestInfo(unsubscribe, mri))

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
        # Hooks
        self.register_hooked(ReportHandlersHook, self.report_handlers)

    @add_call_types
    def report_handlers(self):
        # type: () -> UHandlerInfos
        regexp = r"/%s" % self.name
        info = HandlerInfo(
            regexp, MalcWebSocketHandler, registrar=self.registrar)
        return info

