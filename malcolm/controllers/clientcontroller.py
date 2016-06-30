import functools

from malcolm.core.controller import Controller
from malcolm.core.request import Request
from malcolm.core.method import Method


class ClientController(Controller):
    """Sync a local block with a given remote block"""

    def __init__(self, process, block):
        """
        Args:
            process (Process): The process this should run under
            block (Block): The local block we should be controlling
            client_comms (ClientComms): Should be already connected to a server
                hosting the remote block
        """
        self.q = process.create_queue()
        self.client_comms = process.get_client_comms(block.name)
        assert self.client_comms, \
            "Process doesn't know about block %s" % block.name
        # Call this last as it calls create_methods
        super(ClientController, self).__init__(block=block)

    def create_methods(self):
        """Get methods from remote block and mirror them internally"""
        request = Request.Get(None, self.q, [self.block.name])
        self.client_comms.q.put(request)
        self.log_debug("Waiting for response to Get %s", self.block.name)
        response = self.q.get()
        # Find all the methods
        for aname, amap in response.value.items():
            # TODO: If it has "takes" it's a method, flaky...
            if "takes" in amap:
                yield self.wrap_method(aname, amap)

    def wrap_method(self, method_name, method_map):
        """Take the serialized method map and create a Method from it

        Args:
            method_map (dict): Serialized Method
        """
        method = Method.from_dict(method_name, method_map)
        method.set_function(
            functools.partial(self.call_server_method, method_name))
        self.log_debug("Wrapping method %s", method_name)
        return method

    def call_server_method(self, method_name, parameters, returns):
        """Call method_name on the server

        Args:
            method_name (str): Name of the method
            parameters (Map): Map of arguments to be called with
            returns (Map): Returns map to fill and return
        """
        self.log_debug(dict(parameters))
        request = Request.Post(None, self.q,
                               [self.block.name, method_name], parameters)
        self.client_comms.q.put(request)
        response = self.q.get()
        assert response.type_ == response.RETURN, \
            "Expected Return, got %s" % response.type_
        returns.update(response.value)
        return returns
