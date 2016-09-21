from collections import OrderedDict

from malcolm.comms.pva.pvautil import PvaUtil
from malcolm.core import ClientComms, Request, Subscribe, Response, \
    deserialize_object, serialize_object
from malcolm.core.request import Get, Put, Post, Return, Error
import pvaccess


class PvaClientComms(ClientComms, PvaUtil):
    """A class for a client to communicate with the server"""

    def __init__(self, process, _=None):
        """
        Args:
            name (str): Name for logging
            process (Process): Process for primitive creation
        """
        super(PvaClientComms, self).__init__(process)
        self.name = "PvaClientComms"
        self.set_logger_name(self.name)

    def send_to_server(self, request):
        """Dispatch a request to the server

        Args:
            request(Request): The message to pass to the server
        """
        self.log_debug("Request: %s", request)

        try:

            if isinstance(request, Get):
                self.log_debug("Get message with endpoint: %s", request["endpoint"])
                return_object = self.execute_get(request)

            elif isinstance(request, Put):
                self.log_debug("Put message with endpoint: %s", request["endpoint"])
                self.log_debug("Put message with value: %s", request["value"])
                return_object = self.execute_put(request)

            elif isinstance(request, Post):
                self.log_debug("Post message with endpoint: %s", request["endpoint"])
                self.log_debug("Parameters: %s", request["parameters"])
                return_object = self.execute_rpc(request)

        except:
            # PvAccess error, create the Error message
            return_object = Error(id_=request["id"], message="PvAccess error")

        self.log_debug("Return object: %s", return_object)
        self.send_to_caller(return_object)

    def execute_get(self, request):
        # Connect to the channel
        c = pvaccess.Channel(request["endpoint"][0])
        # Create the path request from the endpoints (not including the block name endpoint)
        path = ".".join(request["endpoint"][1:])
        self.log_debug("path: %s", path)
        # Perform a get and record the response
        response = c.get(path)
        self.log_debug("Response: %s", response)
        # Now create the Return object and populate it with the response
        value = response.toDict(True)
        if 'typeid' in value:
            if value['typeid'] == 'malcolm:core/Error:1.0':
                return_object = Error(id_=request["id"], message=value['message'])
            else:
                return_object = Return(id_=request["id"], value=value)
        else:
            return_object = Error(id_=request["id"], message="No valid return typeid")
        return return_object

    def execute_put(self, request):
        # Connect to the channel
        c = pvaccess.Channel(request["endpoint"][0])
        # Create the path request from the endpoints (not including the block name endpoint)
        path = ".".join(request["endpoint"][1:])
        self.log_debug("path: %s", path)
        # Perform a put, but there is no response available
        c.put(request["value"], path)
        # Now create the Return object and populate it with the response
        return_object = Return(id_=request["id"], value="No return value from put")
        return return_object

    def execute_rpc(self, request):
        method = pvaccess.PvObject({'method': pvaccess.STRING})
        method.set({'method': request["endpoint"][1]})
        # Connect to the channel and create the RPC client
        rpc = pvaccess.RpcClient(request["endpoint"][0], method)
        # Construct the pv object from the parameters
        params = self.dict_to_pv_object(request["parameters"])
        self.log_debug("PvObject parameters: %s", params)
        # Call the method on the RPC object
        response = rpc.invoke(params)
        self.log_debug("Response: %s", response)
        # Now create the Return object and populate it with the response
        value = response.toDict(True)
        if 'typeid' in value:
            if value['typeid'] == 'malcolm:core/Error:1.0':
                return_object = Error(id_=request["id"], message=value['message'])
            else:
                return_object = Return(id_=request["id"], value=value)
        else:
            return_object = Error(id_=request["id"], message="No valid return typeid")
        return return_object