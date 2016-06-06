from collections import OrderedDict
import json

from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop
from tornado.web import Application

from malcolm.core.servercomms import ServerComms
from malcolm.core.request import Request


class MalcolmWebSocketHandler(WebSocketHandler):

    process = None

    def on_message(self, message):
        """
        Pass on received message to Process

        Args:
            message(str): Received message
        """

        d = json.loads(message, object_pairs_hook=OrderedDict())
        request = Request.from_dict(d)
        request.context = self

        self.process.handle_request(request)


class WSServerComms(ServerComms):
    """A class for communication between browser and server"""

    def __init__(self, name, process, port):
        super(WSServerComms, self).__init__(name, process)

        self.name = name
        self.process = process

        MalcolmWebSocketHandler.process = self.process

        self.WSApp = Application([(r"/", MalcolmWebSocketHandler)])
        self.WSApp.listen(port)
        self.loop = IOLoop.current()

    def send_to_client(self, response):
        """Dispatch response to a client

        Args:
            response(Response): The message to pass to the client
        """

        message = json.dumps(response.to_dict())
        response.context.write_message(message)

    def start_recv_loop(self):
        """Start a receive loop to dispatch requests to Process"""
        self.loop.start()

    def stop_recv_loop(self):
        """Stop the receive loop created by start_recv_loop"""
        self.loop.stop()
