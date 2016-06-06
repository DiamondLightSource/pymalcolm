from collections import OrderedDict
import json

from tornado.websocket import WebSocketHandler
from tornado.ioloop import IOLoop
from tornado.web import Application

from malcolm.core.clientcomms import ClientComms
from malcolm.core.request import Response


class MalcolmWebSocketHandler(WebSocketHandler):

    process = None

    def on_message(self, message):
        """
        Pass response from server to process receive queue

        Args:
            message(str): Received message
        """

        d = json.loads(message, object_pairs_hook=OrderedDict())
        response = Response.from_dict(d)
        response.context = self

        self.process.q.put(response)


class WSClientComms(ClientComms):
    """A class for a client to communicate with the server"""

    def __init__(self, name, process, port):
        super(WSClientComms, self).__init__(name, process)

        self.name = name
        self.process = process

        MalcolmWebSocketHandler.process = self.process

        self.WSApp = Application([(r"/", MalcolmWebSocketHandler)])
        self.WSApp.listen(port)
        self.loop = IOLoop.current()

    def send_to_server(self, request):
        """Dispatch a request to the server

        Args:
            request(Request): The message to pass to the server
        """

        message = json.dumps(request.to_dict())
        request.context.write_message(message)

    def start_recv_loop(self):
        """Start a receive loop to dispatch responses to a Method"""
        self.loop.start()

    def stop_recv_loop(self):
        """Stop the receive loop created by start_recv_loop"""
        self.loop.stop()
