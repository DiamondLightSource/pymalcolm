from collections import OrderedDict
from threading import Event, Lock, RLock

import pvaccess

from malcolm.comms.pva.pvautil import PvaUtil
from malcolm.core.cache import Cache
from malcolm.core.loggable import Loggable
from malcolm.core.servercomms import ServerComms
from malcolm.core.methodmeta import method_takes
from malcolm.core.request import Error, Post, Put, Subscribe
from malcolm.core.response import Return
from malcolm.compat import long_


@method_takes()
class PvaServerComms(ServerComms, PvaUtil):
    """A class for communication between pva client and server"""
    CACHE_UPDATE = 0

    def __init__(self, process, _=None):
        super(PvaServerComms, self).__init__(process)

        self.name = "PvaServerComms"
        self.set_logger_name(self.name)

        self._lock = RLock()

        self._current_id = 1
        self._root_id = 0
        self._blocklist = {}
        self._cache = Cache()

        self._server = None
        self._endpoints = {}
        self._cb = None

        self._rpcs = {}
        self._puts = {}
        self._dead_rpcs = []

        # Create the V4 PVA server object
        self.create_pva_server()

        # Add a thread for executing the V4 PVA server
        self.add_spawn_function(self.start_pva_server)

        # Set up the subscription for everything (root down)
        request = Subscribe(None, self.q, [], True)
        request.set_id(self._root_id)
        self.process.q.put(request)

    def _get_unique_id(self):
        with self._lock:
            self._current_id += 1
            return self._current_id

    def _update_block_list(self):
        with self._lock:
            old_blocks = self._blocklist.copy()
            for name in self._cache:
                if name in self._blocklist:
                    old_blocks.pop(name)
                else:
                    # New block, so create the new Pva endpoint
                    self.log_debug("Adding malcolm block to PVA list: %s", name)
                    self._blocklist[name] = self._get_unique_id()
                    self._add_new_pva_channel(name)

            # Now loop over any remaining old blocks and remove their subscriptions
            for name in old_blocks:
                self.log_debug("Removing stale malcolm block: %s", name)

    def _update_cache(self, response):
        if response.changes:
            self.log_debug("Update received: %s", response.changes)
            self._cache.apply_changes(*response.changes)
            # Update the block list to create new PVA channels if required
            self._update_block_list()

    def send_to_client(self, response):
        """Abstract method to dispatch response to a client

        Args:
            response (Response): The message to pass to the client
        """
        if isinstance(response, Return):
            # Notify RPC of return value
            self.log_debug("Response: %s", response)
            if response["id"] in self._rpcs:
                self._rpcs[response["id"]].notify_reply(response)
            elif response["id"] in self._puts:
                self._puts[response["id"]].notify_reply(response)
        elif isinstance(response, Error):
            # Notify RPC of error value
            self.log_debug("Response: %s", response)
            if response["id"] in self._rpcs:
                self._rpcs[response["id"]].notify_reply(response)
            elif response["id"] in self._puts:
                self._puts[response["id"]].notify_reply(response)
        else:
            # Update the cache
            self._update_cache(response)

    def _add_new_pva_channel(self, block):
        """Create a new PVA endpoint for the block name

        Args:
            name (str): The name of the block to create the PVA endpoint for
        """
        self.log_debug("Creating PVA endpoint for %s", block)
        self._endpoints[block] = PvaEndpoint(self.name, block, self._server, self)

    def create_pva_server(self):
        #self.log_debug("Creating PVA server object")
        self._server = pvaccess.PvaServer()

    def start_pva_server(self):
        self.log_debug("Starting PVA server")
        #self._server.listen()
        self._server.startListener()

    def stop_pva_server(self):
        self.log_debug("Executing stop PVA server")
        self._server.stop()

    def register_rpc(self, id, rpc):
        with self._lock:
            self.log_debug("Registering RPC object with ID %d", id)
            self._rpcs[id] = rpc

    def register_put(self, id, put):
        with self._lock:
            self.log_debug("Registering Put object with ID %d", id)
            self._puts[id] = put

    def remove_put(self, id):
        with self._lock:
            self.log_debug("Removing Put object with ID %d", id)
            if id in self._puts:
                if self._puts[id].check_lock():
                    self._puts.pop(id, None)

    def register_dead_rpc(self, id):
        with self._lock:
            self.log_debug("Notifying server that RPC [%d] can be tested for purging", id)
            self._dead_rpcs.append(id)

    def purge_rpcs(self):
        with self._lock:
            rpc_list = list(self._dead_rpcs)
            for id in rpc_list:
                self.log_debug("Testing for purge RPC [%d]", id)
                if id in self._rpcs:
                    if self._rpcs[id].check_lock():
                        # We've gained the lock, so we are OK to purge this RPC
                        self.log_debug("Purging dead RPC [%d]", id)
                        self._rpcs.pop(id, None)
                        self._dead_rpcs.remove(id)
                else:
                    self.log_debug("RPC [%d] was not present (already purged?)", id)
                    if id in self._dead_rpcs:
                        self._dead_rpcs.remove(id)

    def cache_to_pvobject(self, name, paths=None):
        self.log_debug("Cache[%s]: %s", name, self._cache[name])
        # Test parsing the cache to create the PV structure
        try:
            block = self._cache[name]
            if not paths:
                # No paths provided, so just return the whole block
                pv_object = self.dict_to_pv_object(block)
            else:
                #self.log_debug("Path route: %s", paths)
                # List of path lists provided
                # Create empty dict to store the structure
                path_dict = OrderedDict()
                # Create empty dict to store the values
                val_dict = OrderedDict()
                # Loop over each path list
                for path in paths:
                    # Insert the block name as the first endpoint (needed for walking cache)
                    path.insert(0, name)
                    # set pointer to structure dict
                    d = path_dict
                    # set pointer to value dict
                    v = val_dict
                    # set pointer to cache
                    t = self._cache
                    # Loop over each node in the path (except for the last)
                    for node in path[:-1]:
                        #self.log_debug("Node: %s", node)
                        # Update the cache pointer
                        t = t[node]
                        # Check if the structure for this node has already been created
                        if node not in d:
                            # No structure, so create it
                            d[node] = OrderedDict()
                            # Collect and assign the correct type for this structure
                            d[node]["typeid"] = t["typeid"]
                        # Update the structure pointer
                        d = d[node]
                        # Check if the value structure for this node has already been created
                        if node not in v:
                            # No value structure so create it
                            v[node] = OrderedDict()
                        # Update the value pointer
                        v = v[node]
                    # Walk the cache path and update the structure with the final element
                    d[path[-1]] = self._cache.walk_path(path)
                    # Walk the cache path and update the value with the final element
                    v[path[-1]] = self._cache.walk_path(path)
                    #self.log_debug("Walk path: %s", path)
                    #self.log_debug("Path dict: %s", path_dict)
                # Create our PV object from the structure dict
                pv_object = self.dict_to_pv_object_structure(path_dict[name])
                # Set the value of the PV object from the value dict
                pv_object.set(self.strip_type_id(val_dict[name]))
        except:
            raise

        return pv_object

    def get_request(self, block, request):
        self.log_debug("Get request made with: %s", request)
        try:
            # We need to convert the request object into a set of paths
            if "field" not in request:
                pv_object = self.cache_to_pvobject(block)
            else:
                field_dict = request["field"]
                if not field_dict:
                    # The whole block has been requested
                    self.log_debug("Complete block %s requested for pvget", block)
                    # Retrieve the entire block structure
                    pv_object = self.cache_to_pvobject(block)
                else:
                    paths = self.dict_to_path(field_dict)
                    self.log_debug("Paths: %s", paths)
                    pv_object = self.cache_to_pvobject(block, paths)
        except:
            # There has been a failure, return an error object
            err = Error(id_=1, message="Failed to retrieve endpoints")
            response_dict = err.to_dict()
            response_dict.pop("id")
            pv_object = self.dict_to_pv_object(response_dict)

        return pv_object

    def dict_to_path(self, dict_in):
        items = []
        for item in dict_in:
            if not dict_in[item]:
                items.append([item])
            else:
                temp_list = self.dict_to_path(dict_in[item])
                for temp_item in temp_list:
                    if isinstance(temp_item, list):
                        temp_item.insert(0, item)
                        items.append(temp_item)
                    else:
                        items.append([item, temp_item])
        return items


class PvaEndpoint(Loggable):
    def __init__(self, name, block, pva_server, server):
        self.set_logger_name(name)
        self._endpoint = pvaccess.Endpoint()
        self._name = name
        self._block = block
        self._pva_server = pva_server
        self._server = server
        self.log_debug("Registering PVA Endpoint for block %s", self._block)
        self._endpoint.registerEndpointGet(self.get_callback)
        self._endpoint.registerEndpointPut(self.put_callback)
        self._endpoint.registerEndpointRPC(self.rpc_callback)
        #self._endpoint.registerEndpointMonitor(self.monitor_callback)
        self._pva_server.registerEndpoint(self._block, self._endpoint)

#    def monitor_callback(self, request):
#        self.log_debug("Monitor callback called for: %s", self._block)
#        self.log_debug("Request structure: %s", request.toDict())
#        pva_impl = PvaMonitorImplementation()
#        return pva_impl

    def get_callback(self, request):
        self.log_debug("Get callback called for: %s", self._block)
        self.log_debug("Request structure: %s", request.toDict())
        pva_impl = PvaGetImplementation(self._name, request, self._block, self._server)
        return pva_impl

    def put_callback(self, request):
        self.log_debug("Put callback called for: %s", self._block)
        self.log_debug("Request structure: %s", request.toDict())
        put_id = self._server._get_unique_id()
        put = PvaPutImplementation(put_id, self._name, request, self._block, self._server)
        self._server.register_put(put_id, put)
        return put

    def rpc_callback(self, request):
        self.log_debug("Rpc callback called for %s", self._block)
        self.log_debug("Request structure: %s", request)
        # Purge old RPCs
        self._server.purge_rpcs()
        rpc_id = self._server._get_unique_id()
        self.log_debug("RPC ID: %d", rpc_id)
        rpc = PvaRpcImplementation(rpc_id, self._server, self._block, request["method"])
        self._server.register_rpc(rpc_id, rpc)
        return rpc.execute


class PvaGetImplementation(Loggable):
    def __init__(self, name, request, block, server):
        self.set_logger_name(name)
        self._name = name
        self._block = block
        self._server = server
        self._request = request
        self._pv_structure = self._server.get_request(block, request)

    def getPVStructure(self):
        return self._pv_structure

    def get(self):
        # Null operation, the structure already contains the values
        self.log_debug("Get method called")
        self._pv_structure = self._server.get_request(self._block, self._request)


class PvaBlockingImplementation():
    def __init__(self):
        self._response = None
        self._event = Event()
        self._lock = Lock()

    def check_lock(self):
        # Check the lock to see if it is still acquired
        return self._lock.acquire(False)

    def wait_for_reply(self):
        # wait on the reply event
        self._event.wait()

    def notify_reply(self, response):
        self._response = response
        self._event.set()


class PvaPutImplementation(PvaBlockingImplementation, Loggable):
    def __init__(self, id, name, request, block, server):
        super(PvaPutImplementation, self).__init__()
        self.set_logger_name(name)
        self._id = id
        self._name = name
        self._block = block
        self._server = server
        self._request = request
        self._pv_structure = self._server.get_request(block, request)

    def getPVStructure(self):
        return self._pv_structure

    def get(self):
        # Null operation, the structure already contains the values
        self.log_debug("Get method called")
        self._pv_structure = self._server.get_request(self._block, self._request)

    def put(self, pv):
        # Null operation, the structure already contains the values
        self.log_debug("Put method called with: %s", pv)
        self.log_debug("Put method called with: %s", pv.toDict())
        put_dict = pv.toDict()
        endpoints = [self._block]
        endpoints = endpoints + self.dict_to_path(put_dict)
        self.log_debug("Endpoints: %s", endpoints)
        values = self.dict_to_value(put_dict)
        msg = Put(response_queue=self._server.q, endpoint=endpoints, value=values)
        msg.set_id(self._id)
        self._server.send_to_process(msg)
        with self._lock:
            self.wait_for_reply()
            self.log_debug("Put method reply received")
        self._server.remove_put(self._id)

    def dict_to_path(self, dict_in):
        self.log_debug("dict_to_path called with: %s", dict_in)
        items = []
        for item in dict_in:
            self.log_debug("Item: %s", item)
            items.append(item)
            if dict_in[item]:
                if isinstance(dict_in[item], dict):
                    items = items + self.dict_to_path(dict_in[item])
        return items

    def dict_to_value(self, dict_in):
        self.log_debug("dict_to_value called with: %s", dict_in)
        for item in dict_in:
            self.log_debug("Item: %s", item)
            if isinstance(dict_in[item], dict):
               return self.dict_to_value(dict_in[item])
            else:
                return dict_in[item]


class PvaRpcImplementation(PvaBlockingImplementation, Loggable):
    def __init__(self, id, server, block, method):
        super(PvaRpcImplementation, self).__init__()
        self.set_logger_name("PvaRpcImplementation")
        self._id = id
        self._server = server
        self._block = block
        self._method = method

    def parse_variants(self, item_in):
        # Iterate over item_in looking for tuples
        if isinstance(item_in, dict):
            # item_in is a dict so parse each item
            new_dict = OrderedDict()
            for item in item_in:
                new_dict[item] = self.parse_variants(item_in[item])
            return new_dict
        elif isinstance(item_in, list):
            # item_in is a list so parse each item
            new_list = []
            for item in item_in:
                new_list.append(self.parse_variants(item))
            return new_list
        elif isinstance(item_in, tuple):
            # item_in is not a dict or list so check for tuple
            item = self.parse_variants(item_in[0])
            return item
        else:
            # Just return the item as is
            return item_in


    def execute(self, args):
        self.log_debug("Execute %s method called on [%s] with: %s", self._method, self._block, args)
        self.log_debug("Structure: %s", args.getStructureDict())
        # Acquire the lock
        with self._lock:
            # We now need to create the Post message and execute it
            endpoint = [self._block, self._method]
            request = Post(None, self._server.q, endpoint, self.parse_variants(args.toDict(True)))
            request.set_id(self._id)
            self._server.process.q.put(request)

            # Now wait for the Post reply
            self.log_debug("Waiting for reply")
            self.wait_for_reply()
            self.log_debug("Reply received")
            response_dict = OrderedDict()
            if isinstance(self._response, Return):
                response_dict = self._response["value"]
                self.log_debug("Response value : %s", self._response["value"])
            elif isinstance(self._response, Error):
                response_dict = self._response.to_dict()
                response_dict.pop("id")

            if not response_dict:
                pv_object = pvaccess.PvObject(OrderedDict({}), 'malcolm:core/Map:1.0')
            else:
                #pv_object = self._server.dict_to_structure(response_dict)
                #self.log_debug("Pv Object structure created")
                #self.log_debug("%s", self._server.strip_type_id(response_dict))
                #pv_object.set(self._server.strip_type_id(response_dict))
                pv_object = self._server.dict_to_pv_object(response_dict)
            self.log_debug("Pv Object value set: %s", pv_object)
            # Add this RPC to the purge list
            #self._server.register_dead_rpc(self._id)
            return pv_object

#class PvaMonitorImplementation(Loggable):
#    def __init__(self):
#        self.set_logger_name("PvaMonitorImplementation")
#
#    def getPVStructure(self):
#        self.log_debug("getPVStructure called")
#        pv_object = pvaccess.PvObject(OrderedDict({'value': pvaccess.INT}))
#        return pv_object
#
#    def set_event_queue(self, arg1):
#        self.log_debug("setEventQueue called with argument: %s", arg1)
