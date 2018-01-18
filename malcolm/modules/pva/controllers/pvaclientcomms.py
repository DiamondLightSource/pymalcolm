import pvaccess

from malcolm.modules.builtin.controllers import ClientComms
from malcolm.core import Request, Get, Put, Post, Subscribe, Update, Return, \
    Error, Queue, deserialize_object, UnexpectedError, Unsubscribe, Delta
from .pvautil import dict_to_pv_object, strip_tuples


class PvaClientComms(ClientComms):
    """A class for a client to communicate with the server"""

    use_cothread = False
    _monitors = None
    _send_queue = None

    def do_init(self):
        super(PvaClientComms, self).do_init()
        self._monitors = {}
        self._send_queue = Queue()

    def send_to_server(self, request):
        """Dispatch a request to the server

        Args:
            request(Request): The message to pass to the server
        """
        self._send_queue.put(request)
        self.spawn(self._send_to_server)

    def _send_to_server(self):
        request = self._send_queue.get(timeout=0)
        try:
            request = deserialize_object(request, Request)
            response = None
            if isinstance(request, Get):
                response = self._execute_get(request)
            elif isinstance(request, Put):
                response = self._execute_put(request)
            elif isinstance(request, Post):
                response = self._execute_rpc(request)
            elif isinstance(request, Subscribe):
                self._execute_monitor(request)
            elif isinstance(request, Unsubscribe):
                response = self._execute_unsubscribe(request)
            else:
                raise UnexpectedError("Unexpected request %s", request)
        except Exception as e:
            _, response = request.error_response(e)
        if response:
            request.callback(response)

    def _response_from_dict(self, request, d):
        if d.get("typeid", "") == Error.typeid:
            response = Error(request.id, d["message"])
        else:
            response = Return(request.id, d)
        return response

    def _execute_get(self, request):
        path = ".".join(request.path[1:])
        channel = pvaccess.Channel(request.path[0])
        d = channel.get(path).toDict()
        response = self._response_from_dict(request, d)
        return response

    def _execute_put(self, request):
        path = ".".join(request.path[1:])
        channel = pvaccess.Channel(request.path[0])
        channel.put(request.value, path)
        response = Return(request.id)
        return response

    def _execute_monitor(self, request):
        # Connect to the channel
        path = ".".join(request.path[1:])
        channel = pvaccess.Channel(request.path[0])
        self._monitors[request.generate_key()] = channel

        # Store the connection within the monitor set
        def callback(value=None):
            # TODO: ordering is not maintained here...
            # TODO: should we strip_tuples here?
            d = value.toDict(True)
            if d.get("typeid", "") == Error.typeid:
                response = Error(request.id, d["message"])
                self._monitors.pop(request.generate_key())
                channel.unsubscribe("")
            else:
                # TODO: support Deltas properly
                if request.delta:
                    response = Delta(request.id, [[[], d]])
                else:
                    response = Update(request.id, d)
            request.callback(response)

        # Perform a subscribe, but it returns nothing
        channel.subscribe("sub", callback)
        channel.startMonitor(path)
        a = None
        return a

    def _execute_unsubscribe(self, request):
        channel = self._monitors.pop(request.generate_key())
        channel.unsubscribe("sub")
        response = Return(request.id)
        return response

    def _execute_rpc(self, request):
        method = pvaccess.PvObject({'method': pvaccess.STRING})
        method.set({'method': request.path[1]})
        # Connect to the channel and create the RPC client
        rpc = pvaccess.RpcClient(request.path[0], method)
        # Construct the pv object from the parameters
        params = dict_to_pv_object(request.parameters)
        # Call the method on the RPC object
        value = rpc.invoke(params)
        # Now create the Return object and populate it with the response
        d = strip_tuples(value.toDict(True))
        response = self._response_from_dict(request, d)
        return response
