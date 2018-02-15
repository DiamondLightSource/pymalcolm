from annotypes import Anno, TYPE_CHECKING
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect, WebSocketClientConnection

from malcolm.core import Subscribe, deserialize_object, \
    json_decode, json_encode, Response, Error, Unsubscribe, Update, Return, \
    Queue, TimeoutError, Spawned, Request, StringArrayMeta, Widget, \
    ResponseError
from malcolm.modules import builtin

if TYPE_CHECKING:
    from typing import Dict, Tuple, Callable
    Key = Tuple[Callable[[Response], None], int]

with Anno("Hostname of malcolm websocket server"):
    AHostname = str
with Anno("Port number to run up under"):
    APort = int
with Anno("Time to wait for connection"):
    AConnectTimeout = float


class WebsocketClientComms(builtin.controllers.ClientComms):
    """A class for a client to communicate with the server"""

    def __init__(self,
                 mri,  # type: builtin.controllers.AMri
                 hostname="localhost",  # type: AHostname
                 port=8080,  # type: APort
                 connect_timeout=5.0  # type: AConnectTimeout
                 ):
        # type: (...) -> None
        super(WebsocketClientComms, self).__init__(mri, use_cothread=False)
        self.hostname = hostname
        self.port = port
        self.connect_timeout = connect_timeout
        self.loop = IOLoop()
        self._connected_queue = Queue()
        self._spawned = None  # type: Spawned
        # {new_id: (request, old_id}
        self._request_lookup = {}  # type: Dict[int, Tuple[Request, int]]
        # {Subscribe.generator_key(): Subscribe}
        self._subscription_keys = {}  # type: Dict[Key, Subscribe]
        self._next_id = 1
        self._conn = None  # type: WebSocketClientConnection
        # Create read-only attribute for the remotely reachable blocks
        self.remote_blocks = StringArrayMeta(
            "Remotely reachable blocks", tags=[Widget.TABLE.tag()]
        ).create_attribute_model()
        self.field_registry.add_attribute_model(
            "remoteBlocks", self.remote_blocks)

    def do_init(self):
        super(WebsocketClientComms, self).do_init()
        root_subscribe = Subscribe(id=0, path=[".", "blocks"])
        root_subscribe.set_callback(self._update_remote_blocks)
        self._subscription_keys[root_subscribe.generate_key()] = root_subscribe
        self._request_lookup[0] = (root_subscribe, 0)
        self.start_io_loop()

    def _update_remote_blocks(self, response):
        response = deserialize_object(response, Update)
        # TODO: should we spawn here?
        self.remote_blocks.set_value(response.value)

    def start_io_loop(self):
        if self._spawned is None:
            self._conn = None
            self.loop.add_callback(self.recv_loop)
            self._spawned = self.spawn(self.loop.start)
            try:
                self._connected_queue.get(self.connect_timeout)
            except TimeoutError:
                self.stop_io_loop()
                raise

    def stop_io_loop(self):
        if self.loop:
            self.loop.stop()
            self._spawned.wait(timeout=10)
            self._spawned = None

    @gen.coroutine
    def recv_loop(self):
        url = "ws://%s:%d/ws" % (self.hostname, self.port)
        self._conn = yield websocket_connect(
            url, self.loop, connect_timeout=self.connect_timeout - 0.5)
        self._connected_queue.put(True)
        for request in self._subscription_keys.values():
            self._send_request(request)
        while True:
            message = yield self._conn.read_message()
            if message is None:
                for request, old_id in self._request_lookup.values():
                    if not isinstance(request, Subscribe):
                        # Respond with an error
                        response = Error(
                            old_id, ResponseError("Server disconnected"))
                        request.callback(response)
                self.spawn(self._report_fault)
                return
            self.on_message(message)

    def _report_fault(self):
        with self._lock:
            self.transition(self.state_set.FAULT, "Server disconnected")
            self.stop_io_loop()

    def do_disable(self):
        super(WebsocketClientComms, self).do_disable()
        self.stop_io_loop()

    def do_reset(self):
        super(WebsocketClientComms, self).do_reset()
        self.start_io_loop()

    def on_message(self, message):
        """Pass response from server to process receive queue

        Args:
            message(str): Received message
        """
        try:
            self.log.debug("Got message %s", message)
            d = json_decode(message)
            response = deserialize_object(d, Response)
            if isinstance(response, (Return, Error)):
                request, old_id = self._request_lookup.pop(response.id)
                if request.generate_key() in self._subscription_keys:
                    self._subscription_keys.pop(request.generate_key())
                if isinstance(response, Error):
                    # Make the message an exception so it can be raised
                    response.message = ResponseError(response.message)
            else:
                request, old_id = self._request_lookup[response.id]
            response.id = old_id
            # TODO: should we spawn here?
            request.callback(response)
        except Exception:
            # If we don't catch the exception here, tornado will spew odd
            # error messages about 'HTTPRequest' object has no attribute 'path'
            self.log.exception("on_message(%r) failed", message)

    def send_to_server(self, request):
        """Dispatch a request to the server

        Args:
            request (Request): The message to pass to the server
        """
        self.loop.add_callback(self._send_to_server, request)

    def _send_to_server(self, request):
        if isinstance(request, Unsubscribe):
            # If we have an unsubscribe, send it with the same id as the
            # subscribe
            subscribe = self._subscription_keys.pop(request.generate_key())
            new_id = subscribe.id
        else:
            if isinstance(request, Subscribe):
                # If we have an subscribe, store it so we can look it up
                self._subscription_keys[request.generate_key()] = request
            new_id = self._next_id
            self._next_id += 1
            self._request_lookup[new_id] = (request, request.id)
        request.id = new_id
        self._send_request(request)

    def _send_request(self, request):
        message = json_encode(request)
        self.log.debug("Sending message %s", message)
        self._conn.write_message(message)
