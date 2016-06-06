from collections import OrderedDict

from malcolm.core.loggable import Loggable

# Sentinel object to stop the send loop
CLIENT_STOP = object()


class ClientComms(Loggable):
    """Abstract class for dispatching requests to a server and resonses to
    a method"""

    def __init__(self, name, process):
        super(ClientComms, self).__init__(logger_name=name)
        self.process = process
        self.q = self.process.create_queue()
        self._send_spawned = None
        self._current_id = 1
        self.requests = OrderedDict()

    def send_loop(self):
        """Service self.q, sending requests to server"""
        while True:
            request = self.q.get()
            if request is CLIENT_STOP:
                break
            try:
                request.id_ = self._current_id
                self._current_id += 1

                # TODO: Move request store into new method?
                self.requests[request.id_] = request
                self.send_to_server(request)
            except Exception:
                self.log_exception(
                    "Exception sending request %s", request.to_dict())

    def send_to_server(self, request):
        """Abstract method to dispatch request to a server

        Args:
            request (Request): The message to pass to the server
        """
        raise NotImplementedError(
            "Abstract method that must be implemented by deriving class")

    def start(self):
        """Start communications"""
        self._send_spawned = self.process.spawn(self.send_loop)
        self.start_recv_loop()

    def stop(self, timeout=None):
        """Request all communications be stopped and wait for finish

        Args:
            timeout (float): Time in seconds to wait for comms to stop.
            None means wait forever.
        """
        self.q.put(CLIENT_STOP)
        self._send_spawned.wait(timeout=timeout)
        self.stop_recv_loop()

    def start_recv_loop(self):
        """Abstract method to start a receive loop to dispatch responses to a
        a Method"""
        raise NotImplementedError(
            "Abstract method that must be implemented by deriving class")

    def stop_recv_loop(self):
        """Abstract method to stop the receive loop created by
        start_recv_loop"""
        raise NotImplementedError(
            "Abstract method that must be implemented by deriving class")
