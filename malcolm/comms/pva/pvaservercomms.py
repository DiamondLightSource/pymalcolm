from threading import Event, Lock, RLock

import pvaccess

from malcolm.compat import OrderedDict
from malcolm.comms.pva.pvautil import PvaUtil
from malcolm.core.loggable import Loggable
from malcolm.core.servercomms import ServerComms
from malcolm.core.methodmeta import method_takes
from malcolm.core.request import Error, Get, Post, Put, Subscribe
from malcolm.core.response import Return, Update, Delta


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
        self._local_block_list = {}
        self._local_block_id = self._get_unique_id()
        self._remote_block_list = {}
        self._remote_block_id = self._get_unique_id()

        self._server = None
        self._endpoints = {}
        self._cb = None

        self._gets = {}
        self._rpcs = {}
        self._puts = {}
        self._monitors = {}
        self._dead_rpcs = []

        # Create the V4 PVA server object
        self.create_pva_server()

        # Add a thread for executing the V4 PVA server
        self.add_spawn_function(self.start_pva_server)
        self.log_debug("Process name: %s", process.name)
        # Set up the subscription for local blocks
        request = Subscribe(None, self.q, [process.name, 'blocks', 'value'], False)
        request.set_id(self._local_block_id)
        self.process.q.put(request)
        # Set up the subscription for remote blocks
        request = Subscribe(None, self.q, [process.name, 'remoteBlocks', 'value'], False)
        request.set_id(self._remote_block_id)
        self.process.q.put(request)

    def _get_unique_id(self):
        with self._lock:
            self._current_id += 1
            return self._current_id

    def _update_local_block_list(self, block_list):
        with self._lock:
            old_blocks = self._local_block_list.copy()
            for name in block_list:
                if name in self._local_block_list:
                    old_blocks.pop(name)
                else:
                    # New block, so create the new Pva endpoint
                    self.log_debug("Adding malcolm block to PVA list: %s", name)
                    self._local_block_list[name] = self._get_unique_id()
                    self._add_new_pva_channel(name)

            # Now loop over any remaining old blocks and remove their subscriptions
            for name in old_blocks:
                self.log_debug("Removing stale malcolm block: %s", name)

    def _update_remote_block_list(self, block_list):
        with self._lock:
            old_blocks = self._remote_block_list.copy()
            for name in block_list:
                if name in self._remote_block_list:
                    old_blocks.pop(name)
                else:
                    # New block, so create the new Pva endpoint
                    self.log_debug("Adding malcolm block to PVA list: %s", name)
                    self._remote_block_list[name] = self._get_unique_id()
                    self._add_new_pva_channel(name)

            # Now loop over any remaining old blocks and remove their subscriptions
            for name in old_blocks:
                self.log_debug("Removing stale malcolm block: %s", name)

    def send_to_client(self, response):
        """Abstract method to dispatch response to a client

        Args:
            response (Response): The message to pass to the client
        """
        self.log_debug("Response: %s", response)
        if isinstance(response, Return):
            if response["id"] in self._gets:
                self._gets[response["id"]].notify_reply(response)
            elif response["id"] in self._rpcs:
                self._rpcs[response["id"]].notify_reply(response)
            elif response["id"] in self._puts:
                self._puts[response["id"]].notify_reply(response)
            elif response["id"] in self._monitors:
                self._monitors[response["id"]].notify_reply(response)
        elif isinstance(response, Error):
            if response["id"] in self._gets:
                self._gets[response["id"]].notify_reply(response)
            elif response["id"] in self._rpcs:
                self._rpcs[response["id"]].notify_reply(response)
            elif response["id"] in self._puts:
                self._puts[response["id"]].notify_reply(response)
            elif response["id"] in self._monitors:
                self._monitors[response["id"]].notify_reply(response)
        elif isinstance(response, Delta):
            # Check for any monitors registered for this delta
            if response["id"] in self._monitors:
                self._monitors[response["id"]].update(response["changes"])
        elif isinstance(response, Update):
            # Check if the message contains block names
            if response["id"] == self._local_block_id:
                self._update_local_block_list(response["value"])
            if response["id"] == self._remote_block_id:
                self._update_remote_block_list(response["value"])

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

    def register_monitor(self, id, monitor):
        with self._lock:
            self.log_debug("Registering monitor object with ID %d", id)
            self._monitors[id] = monitor

    def register_get(self, id, get):
        with self._lock:
            self.log_debug("Registering Get object with ID %d", id)
            self._gets[id] = get

    def remove_get(self, id):
        with self._lock:
            self.log_debug("Removing Get object with ID %d", id)
            if id in self._gets:
                self._gets.pop(id, None)

    def register_put(self, id, put):
        with self._lock:
            self.log_debug("Registering Put object with ID %d", id)
            self._puts[id] = put

    def remove_put(self, id):
        with self._lock:
            self.log_debug("Removing Put object with ID %d", id)
            if id in self._puts:
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
        # TODO: There is no way to eliminate dead RPC connections
        self._endpoint.registerEndpointRPC(self.rpc_callback)
        # TODO: There is no way to eliminate dead monitors
        # TODO: Monitors do not support deltas
        self._endpoint.registerEndpointMonitor(self.monitor_callback)
        self._pva_server.registerEndpoint(self._block, self._endpoint)

    def monitor_callback(self, request):
        self.log_debug("Monitor callback called for: %s", self._block)
        self.log_debug("Request structure: %s", request.toDict())
        mon_id = self._server._get_unique_id()
        pva_impl = PvaMonitorImplementation(mon_id, request, self._block, self._server)
        pva_impl.send_get_request()
        self._server.register_monitor(mon_id, pva_impl)
        pva_impl.send_subscription()
        return pva_impl

    def get_callback(self, request):
        self.log_debug("Get callback called for: %s", self._block)
        self.log_debug("Request structure: %s", request.toDict())
        get_id = self._server._get_unique_id()
        get = PvaGetImplementation(get_id, request, self._block, self._server)
        get.send_get_request()
        return get

    def put_callback(self, request):
        self.log_debug("Put callback called for: %s", self._block)
        self.log_debug("Request structure: %s", request.toDict())
        put_id = self._server._get_unique_id()
        put = PvaPutImplementation(put_id, request, self._block, self._server)
        put.send_get_request()
        return put

    def rpc_callback(self, request):
        self.log_debug("Rpc callback called for %s", self._block)
        self.log_debug("Request structure: %s", request)
        # Purge old RPCs
        self._server.purge_rpcs()
        rpc_id = self._server._get_unique_id()
        self.log_debug("RPC ID: %d", rpc_id)
        rpc = PvaRpcImplementation(rpc_id, request, self._block, self._server)
        self._server.register_rpc(rpc_id, rpc)
        return rpc.execute


class PvaImplementation(Loggable):
    def __init__(self, id, request, block, server):
        self._id = id
        self._block = block
        self._server = server
        self._request = request
        self._pv_structure = None
        self._response = None
        self._event = Event()
        self._lock = Lock()
        self._pv_structure = None

    def check_lock(self):
        # Check the lock to see if it is still acquired
        return self._lock.acquire(False)

    def wait_for_reply(self, timeout=2.0):
        # wait on the reply event
        self._event.wait(timeout)
        self._event.clear()

    def notify_reply(self, response):
        self._response = response
        self._event.set()

    def send_get_request(self):
        self.log_debug("send_get_request called with request: %s", self._request)
        try:
            self._server.register_get(self._id, self)
            endpoints = [self._block] + self.dict_to_path(self._request.toDict())
            msg = Get(response_queue=self._server.q, endpoint=endpoints)
            msg.set_id(self._id)
            with self._lock:
                self._server.send_to_process(msg)
                self.wait_for_reply()
            self.log_debug("send_get_request received the following response: %s", self._response)
            # Create the reply structure
            response_dict = self._response["value"]
            for ep in reversed(endpoints[1:]):
                response_dict = {ep: response_dict}
            self.log_debug("response_dict: %s", response_dict)
            self._pv_structure = self._server.dict_to_pv_object(response_dict)
        except Exception:
            self.log_exception("Unable to complete send_get_request: %s", self._request)
        self._server.remove_get(self._id)

    def dict_to_path(self, dict_in):
        self.log_debug("dict_to_path called with: %s", dict_in)
        if "field" in dict_in:
            dict_in = dict_in["field"]
        items = []
        for item in dict_in:
            self.log_debug("Item: %s", item)
            items.append(item)
            if dict_in[item]:
                if isinstance(dict_in[item], dict):
                    items = items + self.dict_to_path(dict_in[item])
        return items


class PvaGetImplementation(PvaImplementation):
    def __init__(self, id, request, block, server):
        super(PvaGetImplementation, self).__init__(id, request, block, server)
        self.set_logger_name("PvaGetImplementation")

    def getPVStructure(self):
        return self._pv_structure

    def get(self):
        # Null operation, the structure already contains the values
        self.log_debug("Get method called")


class PvaPutImplementation(PvaImplementation):
    def __init__(self, id, request, block, server):
        super(PvaPutImplementation, self).__init__(id, request, block, server)
        self.set_logger_name("PvaPutImplementation")

    def getPVStructure(self):
        return self._pv_structure

    def get(self):
        self.log_debug("Get method called")
        self.send_get_request()

    def put(self, pv):
        self.log_debug("Put method called with: %s", pv)
        self._server.register_put(self._id, self)
        put_dict = pv.toDict()
        endpoints = [self._block]
        endpoints = endpoints + self.dict_to_path(put_dict)
        self.log_debug("Endpoints: %s", endpoints)
        values = self.dict_to_value(put_dict)
        msg = Put(response_queue=self._server.q, endpoint=endpoints, value=values)
        msg.set_id(self._id)
        with self._lock:
            self._server.send_to_process(msg)
            self.wait_for_reply()
        self._server.remove_put(self._id)

    def dict_to_value(self, dict_in):
        self.log_debug("dict_to_value called with: %s", dict_in)
        if "field" in dict_in:
            dict_in = dict_in["field"]
        for item in dict_in:
            self.log_debug("Item: %s", item)
            if isinstance(dict_in[item], dict):
               return self.dict_to_value(dict_in[item])
            else:
                return dict_in[item]


class PvaRpcImplementation(PvaImplementation):
    def __init__(self, id, request, block, server):
        super(PvaRpcImplementation, self).__init__(id, request, block, server)
        self.set_logger_name("PvaRpcImplementation")
        self._method = request["method"]

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
            try:
                # We now need to create the Post message and execute it
                endpoint = [self._block, self._method]
                request = Post(None, self._server.q, endpoint, self.parse_variants(args.toDict(True)))
                request.set_id(self._id)
                self._server.process.q.put(request)

                # Now wait for the Post reply
                self.log_debug("Waiting for reply")
                self.wait_for_reply(timeout=None)
                self.log_debug("Reply received %s %s", type(self._response), self._response)
                response_dict = OrderedDict()
                if isinstance(self._response, Return):
                    response_dict = self._response["value"]
                    self.log_debug("Response value : %s", response_dict)
                elif isinstance(self._response, Error):
                    response_dict = self._response.to_dict()
                    response_dict.pop("id")

                if not response_dict:
                    pv_object = pvaccess.PvObject(OrderedDict(), 'malcolm:core/Map:1.0')
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
            except Exception:
                self.log_exception("Request %s failed", self._request)


class PvaMonitorImplementation(PvaImplementation):
    def __init__(self, id, request, block, server):
        super(PvaMonitorImplementation, self).__init__(id, request, block, server)
        self.set_logger_name("PvaMonitorImplementation")
        self.mu = pvaccess.MonitorServiceUpdater()
        self._update_required = False
        self._first_update = True

    def send_subscription(self):
        endpoints = [self._block]
        endpoints = endpoints + self.dict_to_path(self._request.toDict())
        self.log_debug("Endpoints: %s", endpoints)
        msg = Subscribe(response_queue=self._server.q, endpoint=endpoints, delta=True)
        msg.set_id(self._id)
        self._server.send_to_process(msg)

    def get_block(self):
        return self._block

    def getPVStructure(self):
        self.log_debug("getPVStructure called")
        return self._pv_structure

    def getUpdater(self):
        self.log_debug("getUpdater called")
        return self.mu

    def update(self, changes):
        self.log_debug("update called: %s", changes)
        for change in changes:
            endpoints = self.dict_to_path(self._request.toDict()) + change[0]
            path = ".".join(endpoints)
            # TODO: hasField() shouldn't be called if not path, but
            # the code below might still need to be executed...
            if path and self._pv_structure.hasField(path):
                new_value = self._server.value_for_pva_set(change[1])
                self._pv_structure[path] = new_value
                self.log_debug("PV updated structure: %s", self._pv_structure)
                self._update_required = True

        # The first update is automatically returned so for the subscription there is no need to update
        if self._first_update:
            self._first_update = False
            self._update_required = False

        self.notify_updates()

    def notify_updates(self):
        if self._update_required:
            self._update_required = False
            self.mu.update()
