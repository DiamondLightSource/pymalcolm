from collections import OrderedDict

from malcolm.core.cache import Cache
from malcolm.core.loggable import Loggable
from malcolm.core.servercomms import ServerComms
from malcolm.core.serializable import Serializable
from malcolm.core.request import Request, Subscribe
from pvaccess import *

class PvaServerComms(ServerComms):
    """A class for communication between pva client and server"""
    CACHE_UPDATE = 0

    def __init__(self, name, process):
        super(PvaServerComms, self).__init__(name, process)

        self.name = name
        self.process = process

        self._current_id = 1
        self._root_id = 0
        self._blocklist = {}
        self._cache = Cache()

        self._server = None
        self._endpoints = {}
        self._cb = None

        # Create the V4 PVA server object
        self.create_pva_server()

        # Set up the subscription for everything (root down)
        request = Subscribe(None, self.q, [], True)
        request.set_id(self._root_id)
        self.process.q.put(request)

        # Add a thread for executing the V4 PVA server
        #self.add_spawn_function(self.start_v4)

    def _update_block_list(self):
        old_blocks = self._blocklist.copy()
        for name in self._cache:
            if name in self._blocklist:
                old_blocks.pop(name)
            else:
                # New block, so create the new Pva endpoint
                self.log_debug("Adding malcolm block to PVA list: %s", name)
                self._current_id += 1
                self._blocklist[name] = self._current_id
                self._add_new_pva_channel(name)

        # Now loop over any remaining old blocks and remove their subscriptions
        for name in old_blocks:
            self.log_debug("Removing stale malcolm block: %s", name)

    def _update_cache(self, response):
        if response.changes:
            #self.log_debug("Update received: %s", response.changes)
            self._cache.apply_changes(*response.changes)
            # Update the block list to create new PVA channels if required
            self._update_block_list()

    def send_to_client(self, response):
        """Abstract method to dispatch response to a client

        Args:
            response (Response): The message to pass to the client
        """
        # Update the cache
        self._update_cache(response)

    def _add_new_pva_channel(self, name):
        """Create a new PVA endpoint for the block name

        Args:
            name (str): The name of the block to create the PVA endpoint for
        """
        self.log_debug("Creating PVA endpoint for %s", name)
        self._endpoints[name] = PvaEndpoint(name, self._server, self)

    def create_pva_server(self):
        self.log_debug("Creating PVA server object")
        self._server = PvaServer()

    def start_pva_server(self):
        self.log_debug("Starting PVA server")
        self._server.listen(8)

    def stop_pva_server(self):
        self.log_debug("Executing stop PVA server")
        self._server.stop()

    def cache_to_pvobject(self, name, paths=None):
        #self.log_debug("Cache[%s]: %s", name, self._cache[name])
        # Test parsing the cache to create the PV structure
        block = self._cache[name]
        if not paths:
            pv_object = self.dict_to_structure(block)
            #self.log_debug("Structure: %s", structure)
            pv_object.set(self.strip_type_id(block))
        else:
            path_dict = OrderedDict()
            for path in paths:
                path_dict[path] = self.dict_to_structure(block[path])
            pv_object = PvObject(path_dict)
            for path in paths:
                pv_object.set({path: self.strip_type_id(block[path])})

        return pv_object

    def dict_to_structure(self, dict_in):
        structure = OrderedDict()
        typeid = None
        for item in dict_in:
            #self.log_debug("ITEM: %s", item)
            if item == "typeid":
                typeid = dict_in[item]
            else:
                if isinstance(dict_in[item], str):
                    structure[item] = STRING
                elif isinstance(dict_in[item], bool):
                    structure[item] = BOOLEAN
                elif isinstance(dict_in[item], int):
                    structure[item] = INT
                elif isinstance(dict_in[item], list):
                    #self.log_debug("List found: %s", item)
                    if not dict_in[item]:
                        structure[item] = [STRING]
                    else:
                        if isinstance(dict_in[item][0], str):
                            structure[item] = [STRING]
                        if isinstance(dict_in[item][0], bool):
                            structure[item] = [BOOLEAN]
                        if isinstance(dict_in[item][0], int):
                            structure[item] = [INT]
                elif isinstance(dict_in[item], OrderedDict):
                    #self.log_debug("dict found: %s", item)
                    structure[item] = self.dict_to_structure(dict_in[item])
        #self.log_debug("Creating PvObject")
        try:
            if not structure:
                structure["empty"] = STRING
            if not typeid:
                pv_object = PvObject(structure)
            else:
                pv_object = PvObject(structure, typeid)
        except:
            self.log_debug("*** Exception ***")
            self.log_debug(structure)
            self.log_debug(typeid)
            self.log_debug("*** ********* ***")
        #self.log_debug("Returning...")
        return pv_object

    def strip_type_id(self, dict_in):
        dict_out = OrderedDict()
        for item in dict_in:
            if item != "typeid":
                if isinstance(dict_in[item], OrderedDict):
                    dict_out[item] = self.strip_type_id(dict_in[item])
                else:
                    dict_out[item] = dict_in[item]
        return dict_out

class PvaEndpoint(Endpoint, Loggable):
    def __init__(self, name, pva_server, server):
        super(PvaEndpoint, self).__init__()
        self.set_logger_name("sc")
        self._name = name
        self._pva_server = pva_server
        self._server = server
        self.log_debug("Testing...")
        self.registerEndpointGet(self.get_callback)
        self._pva_server.registerEndpoint(self._name, self)
        self.log_debug("Registered...")

    def get_callback(self, request):
        self.log_debug("Get callback called for: %s", self._name)
        self.log_debug("Request structure: %s", request.toDict())
        # We need to convert the request object into a set of paths
        if "field" not in request:
            pv_object = self._server.cache_to_pvobject(self._name)
        else:
            field_dict = request["field"]
            if not field_dict:
                # The whole block has been requested
                self.log_debug("Complete block %s requested for pvget", self._name)
                # Retrieve the entire block structure
                pv_object = self._server.cache_to_pvobject(self._name)
            else:
                paths = []
                # Create the list of paths
                for field in field_dict:
                    paths.append(field)
                pv_object = self._server.cache_to_pvobject(self._name, paths)

        pva_impl = PvaGetImplementation(pv_object)
        return pva_impl


class PvaGetImplementation:
    def __init__(self, structure):
        self.pvStructure = structure

    def getPVStructure(self):
        return self.pvStructure

    def get(self):
        # Null operation, the structure already contains the values
        print 'get(self)'
        #self.pvStructure['attribute.value'] = 5

