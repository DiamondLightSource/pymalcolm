from tornado import gen
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

from malcolm.modules.builtin.controllers import ClientComms
from malcolm.core import Subscribe, deserialize_object, method_also_takes, \
    json_decode, json_encode, Response, Error, Unsubscribe, Update, Return, \
    Queue, TimeoutError
from malcolm.modules.builtin.vmetas import StringMeta, NumberMeta, \
    StringArrayMeta
from malcolm.tags import widget


@method_also_takes(
    "hostname", StringMeta("Hostname of malcolm websocket server"), "localhost",
    "port", NumberMeta("int32", "Port number to run up under"), 8080,
    "connectTimeout", NumberMeta("float64", "Time to wait for connection"), 5.0)
class WebsocketClientComms(ClientComms):
    """A class for a client to communicate with the server"""
    use_cothread = False
    # Attribute
    remote_blocks = None

    loop = None
    _conn = None
    _spawned = None
    _connected_queue = None
    # {new_id: (request, old_id}
    _request_lookup = None
    # {Subscribe.generator_key(): Subscribe}
    _subscription_keys = {}
    _next_id = 1

    def create_attribute_models(self):
        for y in super(WebsocketClientComms, self).create_attribute_models():
            yield y
        # Create read-only attribute for the remotely reachable blocks
        meta = StringArrayMeta(
            "Remotely reachable blocks", tags=[widget("table")])
        self.remote_blocks = meta.create_attribute_model()
        yield "remoteBlocks", self.remote_blocks, None

    def do_init(self):
        super(WebsocketClientComms, self).do_init()
        self.loop = IOLoop()
        self._request_lookup = {}
        self._subscription_keys = {}
        self._connected_queue = Queue()
        root_subscribe = Subscribe(
            id=0, path=[".", "blocks"], callback=self._update_remote_blocks)
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
                self._connected_queue.get(self.params.connectTimeout)
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
        url = "ws://%(hostname)s:%(port)d/ws" % self.params
        self._conn = yield websocket_connect(
            url, self.loop, connect_timeout=self.params.connectTimeout - 0.5)
        self._connected_queue.put(True)
        for request in self._subscription_keys.values():
            self._send_request(request)
        while True:
            message = yield self._conn.read_message()
            if message is None:
                for request, old_id in self._request_lookup.values():
                    if not isinstance(request, Subscribe):
                        # Respond with an error
                        response = Error(old_id, message="Server disconnected")
                        request.callback(response)
                self.spawn(self._report_fault)
                return
            self.on_message(message)

    def _report_fault(self):
        with self._lock:
            self.transition(self.stateSet.FAULT, "Server disconnected")
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
            else:
                request, old_id = self._request_lookup[response.id]
            response.set_id(old_id)
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
        request.set_id(new_id)
        self._send_request(request)

    def _send_request(self, request):
        message = json_encode(request)
        self.log.debug("Sending message %s", message)
        self._conn.write_message(message)
