from malcolm.core.loggable import Loggable

# Sentinel object to stop the send loop
SERVER_STOP = object()


class ServerComms(Loggable):
    """Abstract class for dispatching requests to a process and responses to a
    client"""

    def __init__(self, name, process):
        super(ServerComms, self).__init__(logger_name=name)
        self.process = process
        self.q = self.process.create_queue()
        self._send_spawned = None

    def send_loop(self):
        """Service self.q, sending responses to client"""
        while True:
            response = self.q.get()
            if response is SERVER_STOP:
                break
            try:
                self.send_to_client(response)
            except Exception:
                self.log_exception(
                    "Exception sending response %s", response.to_dict())

    def send_to_client(self, response):
        """Abstract method to dispatch response to a client

        Args:
            response (Response): The message to pass to the client
        """
        raise NotImplementedError(
            "Abstract method that must be implemented by deriving class")

    def send_to_process(self, request):
        """Send request to process"""
        self.process.q.put(request)

    def start(self):
        """Start communications"""
        self._send_spawned = self.process.spawn(self.send_loop)
        self.start_recv_loop()

    def start_recv_loop(self):
        """Abstract method to start a recieve loop to dispatch requests to
        Process"""
        raise NotImplementedError(
            "Abstract method that must be implemented by deriving class")

    def stop(self, timeout=None):
        """Request all communications be stopped and wait for finish

        Args:
            timeout (float): Time in seconds to wait for comms to stop.
            None means wait forever.
        """
        self.q.put(SERVER_STOP)
        self._send_spawned.wait(timeout=timeout)
        self.stop_recv_loop()

    def stop_recv_loop(self):
        """Abstract method to stop the receive loop created by
        start_recv_loop"""
        raise NotImplementedError(
            "Abstract method that must be implemented by deriving class")
