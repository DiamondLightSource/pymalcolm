from collections import OrderedDict

from malcolm.core import ClientComms, Request, Subscribe, Response, \
    deserialize_object, serialize_object
from malcolm.core.request import Get, Return, Error
import pvaccess


class PvaClientComms(ClientComms):
    """A class for a client to communicate with the server"""

    def __init__(self, process, _=None):
        """
        Args:
            name (str): Name for logging
            process (Process): Process for primitive creation
        """
        self.name = "PvaClientComms"
        super(PvaClientComms, self).__init__(self.name, process)

    def send_to_server(self, request):
        """Dispatch a request to the server

        Args:
            request(Request): The message to pass to the server
        """
        self.log_debug("Request: %s", request)

        if isinstance(request, Get):
            self.log_debug("Endpoint: %s", request["endpoint"][0])
            try:
                # Connect to the channel
                c = pvaccess.Channel(request["endpoint"][0])
                # Perform a get and record the response
                response = c.get(request["endpoint"][1])
                self.log_debug("Response: %s", response)
                # Now create the Return object and populate it with the response
                return_object = Return(id_=request["id"], value=response.toDict())
            except:
                # PvAccess error, create the Error message
                return_object = Error(id_=request["id"], message="To be determined")

            self.log_debug("Return object: %s", return_object)
            self.send_to_caller(return_object)


#    def subscribe_server_blocks(self, _):
#        """Subscribe to process blocks"""
#        request = Subscribe(None, None, [".", "blocks", "value"])
#        request.set_id(self.SERVER_BLOCKS_ID)
#        self.loop.add_callback(self.send_to_server, request)
