from collections import OrderedDict

from malcolm.core.loggable import Loggable
from malcolm.core.spawnable import Spawnable


class ClientComms(Loggable, Spawnable):
    """Abstract class for dispatching requests to a server and resonses to
    a method"""
    # The id that will be use for subscriptions to the blocks the server has
    SERVER_BLOCKS_ID=0

    def __init__(self, name, process):
        super(ClientComms, self).__init__(logger_name=name)
        self.process = process
        self.q = self.process.create_queue()
        self._current_id = 1
        self.requests = OrderedDict()
        self.add_spawn_function(self.send_loop,
                                self.make_default_stop_func(self.q))

    def send_loop(self):
        """Service self.q, sending requests to server"""
        while True:
            request = self.q.get()
            if request is Spawnable.STOP:
                break
            try:
                request.set_id(self._current_id)
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

    def send_to_caller(self, response):
        if response.id_ == self.SERVER_BLOCKS_ID:
            assert response.type_ == response.UPDATE, \
                "Expected server blocks Update, got %s" % response
            self.process.update_block_list(self, response.value)
        else:
            request = self.requests[response.id_]
            request.response_queue.put(response)
