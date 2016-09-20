from collections import OrderedDict
import json

from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

from malcolm.core import ClientComms, Request, Subscribe, Response, \
    deserialize_object, serialize_object, method_takes
from malcolm.core.vmetas import StringMeta, NumberMeta


@method_takes(
    "hostname", StringMeta("Hostname of malcolm websocket server"), "localhost",
    "port", NumberMeta("int32", "Port number to run up under"), 8080)
class WebsocketClientComms(ClientComms):
    """A class for a client to communicate with the server"""

    def __init__(self, process, params):
        """
        Args:
            process (Process): Process for primitive creation
            params (Map): Parameters map
        """
        super(WebsocketClientComms, self).__init__(process)
        self.url = "ws://%(hostname)s:%(port)d/ws" % params
        self.set_logger_name(self.url)
        # TODO: Are we starting one or more IOLoops here?
        self.loop = IOLoop.current()
        self.conn = websocket_connect(
            self.url, callback=self.subscribe_server_blocks,
            on_message_callback=self.on_message)
        self.add_spawn_function(self.loop.start, self.stop_recv_loop)

    def on_message(self, message):
        """
        Pass response from server to process receive queue

        Args:
            message(str): Received message
        """
        try:
            self.log_debug("Got message %s", message)
            d = json.loads(message, object_pairs_hook=OrderedDict)
            response = deserialize_object(d, Response)
            self.send_to_caller(response)
        except Exception as e:
            # If we don't catch the exception here, tornado will spew odd
            # error messages about 'HTTPRequest' object has no attribute 'path'
            self.log_exception(e)

    def send_to_server(self, request):
        """Dispatch a request to the server

        Args:
            request(Request): The message to pass to the server
        """
        message = json.dumps(serialize_object(request))
        self.conn.result().write_message(message)

    def stop_recv_loop(self):
        # This is the only thing that is safe to do from outside the IOLoop
        # thread
        self.loop.add_callback(self.loop.stop)

    def subscribe_server_blocks(self, _):
        """Subscribe to process blocks"""
        request = Subscribe(None, None, [".", "blocks", "value"])
        request.set_id(self.SERVER_BLOCKS_ID)
        self.loop.add_callback(self.send_to_server, request)
