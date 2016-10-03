from collections import OrderedDict
import json
import logging

from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler, asynchronous
from tornado.httpserver import HTTPServer

from malcolm.core import ServerComms, deserialize_object, serialize_object, \
    Request, Get, Return, Error, Post, method_takes
from malcolm.core.vmetas import NumberMeta


class MalcWebSocketHandler(WebSocketHandler):  # pylint:disable=abstract-method

    servercomms = None

    def on_message(self, message):
        """
        Pass on received message to Process

        Args:
            message(str): Received message
        """

        logging.debug(message)
        d = json.loads(message, object_pairs_hook=OrderedDict)
        request = deserialize_object(d, Request)
        request.context = self
        self.servercomms.on_request(request)


class MalcBlockHandler(RequestHandler):

    servercomms = None

    @asynchronous
    def get(self, endpoint_str):
        endpoint = endpoint_str.split("/")
        request = Get(self, None, endpoint)
        self.servercomms.on_request(request)

    # curl --data 'parameters={"name": "me"}' http://localhost:8888/blocks/hello/say_hello
    @asynchronous
    def post(self, endpoint_str):
        endpoint = endpoint_str.split("/")
        parameters = json.loads(self.get_body_argument("parameters"))
        request = Post(self, None, endpoint, parameters)
        self.servercomms.on_request(request)


@method_takes("port", NumberMeta("int32", "Port number to run up under"), 8080)
class WebsocketServerComms(ServerComms):
    """A class for communication between browser and server"""

    def __init__(self, process, params):
        super(WebsocketServerComms, self).__init__(process)
        self.set_logger_name("WebsocketServerComms(%(port)d)" % params)
        MalcWebSocketHandler.servercomms = self
        MalcBlockHandler.servercomms = self

        application = Application([
            (r"/blocks/(.*)", MalcBlockHandler),
            (r"/ws", MalcWebSocketHandler)
        ])
        self.server = HTTPServer(application)
        self.server.listen(int(params["port"]))
        self.loop = IOLoop.current()
        self.add_spawn_function(self.loop.start, self.stop_recv_loop)

    def send_to_client(self, response):
        """Dispatch response to a client

        Args:
            response(Response): The message to pass to the client
        """
        self.loop.add_callback(self._send_to_client, response)

    def _send_to_client(self, response):
        if isinstance(response.context, MalcWebSocketHandler):
            message = json.dumps(serialize_object(response))
            response.context.write_message(message)
        else:
            if isinstance(response, Return):
                message = json.dumps(serialize_object(response.value))
                response.context.finish(message + "\n")
            else:
                if isinstance(response, Error):
                    message = response.message
                else:
                    message = "Unknown response %s" % type(response)
                response.context.set_status(500, message)
                response.context.write_error(500)

    def on_request(self, request):
        """
        Pass on received request to Process

        Args:
            request (Request): Received request with context but no q
        """

        request.response_queue = self.q
        if hasattr(request, "endpoint") and len(request.endpoint) > 0 and \
                request.endpoint[0] == ".":
            # We're talking about the process block, so fill in the right name
            request.endpoint[0] = self.process.name
        self.process.q.put(request)

    def stop_recv_loop(self):
        # This is the only thing that is safe to do from outside the IOLoop
        # thread
        self.loop.add_callback(self.server.stop)
        self.loop.add_callback(self.loop.stop)
