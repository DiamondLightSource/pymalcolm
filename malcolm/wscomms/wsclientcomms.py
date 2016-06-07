from collections import OrderedDict
import json

from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

from malcolm.core.clientcomms import ClientComms
from malcolm.core.request import Response


class WSClientComms(ClientComms):
    """A class for a client to communicate with the server"""

    def __init__(self, name, process, url):
        """
        Args:
            name (str): Name for logging
            process (Process): Process for primitive creation
            url (str): Url for websocket connection. E.g. ws://localhost:8888/ws
        """
        super(WSClientComms, self).__init__(name, process)

        self.name = name
        self.process = process
        self.url = url
        # TODO: Are we starting one or more IOLoops here?
        self.loop = IOLoop.current()
        self.conn = websocket_connect(url, on_message_callback=self.on_message)
        self._loop_spawned = None

    def on_message(self, message):
        """
        Pass response from server to process receive queue

        Args:
            message(str): Received message
        """
        self.log_debug("Got message %s", message)
        d = json.loads(message, object_pairs_hook=OrderedDict)
        response = Response.from_dict(d)
        self.send_to_caller(response)

    def send_to_server(self, request):
        """Dispatch a request to the server

        Args:
            request(Request): The message to pass to the server
        """

        message = json.dumps(request.to_dict())
        self.conn.result().write_message(message)

    def start_recv_loop(self):
        """Start a receive loop to dispatch responses to a Method"""
        self._loop_spawned = self.process.spawn(self.loop.start)

    def stop_recv_loop(self):
        """Stop the receive loop created by start_recv_loop"""
        # This is the only thing that is safe to do from outside the IOLoop
        # thread
        self.loop.add_callback(self.loop.stop)
        self._loop_spawned.wait()
