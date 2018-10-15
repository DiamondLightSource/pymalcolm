from annotypes import Anno, TYPE_CHECKING
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect, WebSocketClientConnection

from malcolm.core import Subscribe, deserialize_object, \
    json_decode, json_encode, Response, Error, Update, Return, \
    Queue, TimeoutError, Spawned, Request, StringArrayMeta, Widget, \
    ResponseError, DEFAULT_TIMEOUT, Context, Delta, BlockModel, NTScalar, \
    BlockMeta, Put, Post
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
                 connect_timeout=DEFAULT_TIMEOUT  # type: AConnectTimeout
                 ):
        # type: (...) -> None
        super(WebsocketClientComms, self).__init__(mri, use_cothread=False)
        self.hostname = hostname
        self.port = port
        self.connect_timeout = connect_timeout
        self.loop = IOLoop()
        self._connected_queue = Queue()
        self._response_queue = Queue()
        self._spawned = None  # type: Spawned
        # {new_id: request}
        self._request_lookup = {}  # type: Dict[int, Request]
        self._next_id = 1
        self._conn = None  # type: WebSocketClientConnection
        # Create read-only attribute for the remotely reachable blocks
        self.remote_blocks = StringArrayMeta(
            "Remotely reachable blocks", tags=[Widget.TEXTINPUT.tag()]
        ).create_attribute_model()
        self.field_registry.add_attribute_model(
            "remoteBlocks", self.remote_blocks)

    def do_init(self):
        super(WebsocketClientComms, self).do_init()
        self.start_io_loop()
        root_subscribe = Subscribe(path=[".", "blocks"])
        root_subscribe.set_callback(self._update_remote_blocks)
        self.loop.add_callback(self._send_request, root_subscribe)

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
        self._connected_queue.put(None)
        while True:
            message = yield self._conn.read_message()
            if message is None:
                for request in self._request_lookup.values():
                    callback, response = request.error_response(
                        ResponseError("Server disconnected"))
                    callback(response)
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
                request = self._request_lookup.pop(response.id)
                if isinstance(response, Error):
                    # Make the message an exception so it can be raised
                    response.message = ResponseError(response.message)
            else:
                request = self._request_lookup[response.id]
            # TODO: should we spawn here?
            request.callback(response)
        except Exception:
            # If we don't catch the exception here, tornado will spew odd
            # error messages about 'HTTPRequest' object has no attribute 'path'
            self.log.exception("on_message(%r) failed", message)

    def sync_proxy(self, mri, block):
        """Abstract method telling the ClientComms to sync this proxy Block
        with its remote counterpart. Should wait until it is connected

        Args:
            mri (str): The mri for the remote block
            block (BlockModel): The local proxy Block to keep in sync
        """
        # Send a root Subscribe to the server
        subscribe = Subscribe(path=[mri], delta=True)
        done_queue = Queue()

        def handle_response(response):
            # type: (Response) -> None
            self._response_queue.put((response, block))
            self.spawn(self._handle_response).get()
            done_queue.put(None)

        subscribe.set_callback(handle_response)
        self.loop.add_callback(self._send_request, subscribe)
        done_queue.get(timeout=DEFAULT_TIMEOUT)

    def _handle_response(self):
        with self.changes_squashed:
            response, block = self._response_queue.get(timeout=0)
            if not isinstance(response, Delta):
                # Return or Error is the end of our subscription, log and ignore
                self.log.debug("Proxy got response %r", response)
                return
            for change in response.changes:
                try:
                    self._handle_change(block, change)
                except Exception:
                    self.log.exception("Error handling %s", response)
                    raise

    def _handle_change(self, block, change):
        path = change[0]
        if len(path) == 0:
            assert len(change) == 2, \
                "Can't delete root block with change %r" % (change,)
            self._regenerate_block(block, change[1])
        elif len(path) == 1 and path[0] not in ("health", "meta"):
            if len(change) == 1:
                # Delete a field
                block.remove_endpoint(path[1])
            else:
                # Change a single field of the block
                block.set_endpoint_data(path[1], change[1])
        else:
            block.apply_change(path, *change[1:])

    def _regenerate_block(self, block, d):
        for field in list(block):
            if field not in ("health", "meta"):
                block.remove_endpoint(field)
        for field, value in d.items():
            if field == "health":
                # Update health attribute
                value = deserialize_object(value)  # type: NTScalar
                block.health.set_value(
                    value=value.value,
                    alarm=value.alarm,
                    ts=value.timeStamp)
            elif field == "meta":
                value = deserialize_object(value)  # type: BlockMeta
                meta = block.meta  # type: BlockMeta
                for k in meta.call_types:
                    meta.apply_change([k], value[k])
            elif field != "typeid":
                # No need to set writeable_functions as the server will do it
                block.set_endpoint_data(field, value)

    def send_put(self, mri, attribute_name, value):
        """Abstract method to dispatch a Put to the server

        Args:
            mri (str): The mri of the Block
            attribute_name (str): The name of the Attribute within the Block
            value: The value to put
        """
        q = Queue()
        request = Put(
            path=[mri, attribute_name, "value"],
            value=value)
        request.set_callback(q.put)
        self.loop.add_callback(self._send_request, request)
        response = q.get()
        if isinstance(response, Error):
            raise response.message
        else:
            return response.value

    def send_post(self, mri, method_name, **params):
        """Abstract method to dispatch a Post to the server

        Args:
            mri (str): The mri of the Block
            method_name (str): The name of the Method within the Block
            params: The parameters to send

        Returns:
            The return results from the server
        """
        q = Queue()
        request = Post(
            path=[mri, method_name],
            parameters=params)
        request.set_callback(q.put)
        self.loop.add_callback(self._send_request, request)
        response = q.get()
        if isinstance(response, Error):
            raise response.message
        else:
            return response.value

    def _send_request(self, request):
        # Called in tornado thread
        request.id = self._next_id
        self._next_id += 1
        self._request_lookup[request.id] = request
        message = json_encode(request)
        self.log.debug("Sending message %s", message)
        self._conn.write_message(message)
