from collections import OrderedDict
import json

from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.httpserver import HTTPServer

from malcolm.core.servercomms import ServerComms
from malcolm.core.request import Request


class MalcolmWebSocketHandler(WebSocketHandler):

    servercomms = None

    def on_message(self, message):
        """
        Pass on received message to Process

        Args:
            message(str): Received message
        """

        d = json.loads(message, object_pairs_hook=OrderedDict)
        request = Request.from_dict(d)
        request.context = self
        self.servercomms.on_request(request)


class WSServerComms(ServerComms):
    """A class for communication between browser and server"""

    def __init__(self, name, process, port):
        super(WSServerComms, self).__init__(name, process)

        self.name = name
        self.process = process
        # The Result object for the IOLoop start() thread
        self._loop_spawned = None

        MalcolmWebSocketHandler.servercomms = self

        application = Application([(r"/ws", MalcolmWebSocketHandler)])
        self.server = HTTPServer(application)
        self.server.listen(port)
        self.loop = IOLoop.current()

    def send_to_client(self, response):
        """Dispatch response to a client

        Args:
            response(Response): The message to pass to the client
        """

        message = json.dumps(response.to_dict())
        self.log_debug("Sending to client %s", message)
        response.context.write_message(message)

    def on_request(self, request):
        """
        Pass on received request to Process

        Args:
            request (Request): Received request with context but no q
        """

        request.response_queue = self.q
        self.process.handle_request(request)

    def start_recv_loop(self):
        """Start a receive loop to dispatch requests to Process"""
        self._loop_spawned = self.process.spawn(self.loop.start)

    def stop_recv_loop(self):
        """Stop the receive loop created by start_recv_loop"""
        # This is the only thing that is safe to do from outside the IOLoop
        # thread
        self.loop.add_callback(self.server.stop)
        self.loop.add_callback(self.loop.stop)
        self._loop_spawned.wait()
