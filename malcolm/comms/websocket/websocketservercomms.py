from collections import OrderedDict
import json
import logging

from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.httpserver import HTTPServer

from malcolm.core.servercomms import ServerComms
from malcolm.core.serializable import deserialize_object, serialize_object
from malcolm.core.request import Request


class MalcolmWebSocketHandler(WebSocketHandler):

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


class WebsocketServerComms(ServerComms):
    """A class for communication between browser and server"""

    def __init__(self, name, process, port):
        super(WebsocketServerComms, self).__init__(name, process)

        self.name = name
        self.process = process

        MalcolmWebSocketHandler.servercomms = self

        application = Application([(r"/ws", MalcolmWebSocketHandler)])
        self.server = HTTPServer(application)
        self.server.listen(port)
        self.loop = IOLoop.current()
        self.add_spawn_function(self.loop.start, self.stop_recv_loop)

    def send_to_client(self, response):
        """Dispatch response to a client

        Args:
            response(Response): The message to pass to the client
        """

        message = json.dumps(serialize_object(response))
        self.log_debug("Sending to client %s", message)
        response.context.write_message(message)

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
