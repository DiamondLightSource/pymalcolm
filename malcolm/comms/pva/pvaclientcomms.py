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

        if isinstance(request, Get):
            self.log_debug("Get message with endpoint: %s", request["endpoint"])
            try:
                # Connect to the channel
                c = pvaccess.Channel(request["endpoint"][0])
                # Create the path request from the endpoints (not including the block name endpoint)
                path = ""
                for item in request["endpoint"][1:]:
                    path = path + item + "."
                self.log_debug("path: %s", path[:-1])
                # Perform a get and record the response
                response = c.get(path[:-1])
                self.log_debug("Response: %s", response)
                # Now create the Return object and populate it with the response
                value=response.toDict(True)
                if 'typeid' in value:
                    if value['typeid'] == 'malcolm:core/Error:1.0':
                        return_object = Error(id_=request["id"], message=value['message'])
                    else:
                        return_object = Return(id_=request["id"], value=value)
                else:
                    return_object = Error(id_=request["id"], message="No valid return typeid")
            except:
                # PvAccess error, create the Error message
                return_object = Error(id_=request["id"], message="PvAccess error")

            self.log_debug("Return object: %s", return_object)
            self.send_to_caller(return_object)

        elif isinstance(request, Put):
            self.log_debug("Put message with endpoint: %s", request["endpoint"])
            self.log_debug("Put message with value: %s", request["value"])
            try:
                # Connect to the channel
                c = pvaccess.Channel(request["endpoint"][0])
                # Create the path request from the endpoints (not including the block name endpoint)
                path = ""
                for item in request["endpoint"][1:]:
                    path = path + item + "."
                self.log_debug("path: %s", path[:-1])
                # Perform a put, but there is no response available
                c.put(request["value"], path[:-1])
                # Now create the Return object and populate it with the response
                return_object = Return(id_=request["id"], value="No return value from put")
            except:
                # PvAccess error, create the Error message
                return_object = Error(id_=request["id"], message="PvAccess error")

            self.log_debug("Return object: %s", return_object)
            self.send_to_caller(return_object)

        elif isinstance(request, Post):
            self.log_debug("Post message with endpoint: %s", request["endpoint"])
            self.log_debug("Parameters: %s", request["parameters"])
            try:
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
                value=response.toDict(True)
                if 'typeid' in value:
                    if value['typeid'] == 'malcolm:core/Error:1.0':
                        return_object = Error(id_=request["id"], message=value['message'])
                    else:
                        return_object = Return(id_=request["id"], value=value)
                else:
                    return_object = Error(id_=request["id"], message="No valid return typeid")
            except:
                # PvAccess error, create the Error message
                return_object = Error(id_=request["id"], message="PvAccess error")

            self.log_debug("Return object: %s", return_object)
            self.send_to_caller(return_object)

