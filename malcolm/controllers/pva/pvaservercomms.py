import pvaccess

from malcolm.core import Loggable, Process, Queue, Get, Put, Post, Subscribe, \
    Error, ResponseError, Map
from malcolm.controllers.builtin import ServerComms
from .pvautil import dict_to_pv_object, value_for_pva_set


class PvaServerComms(ServerComms):
    """A class for communication between pva client and server"""
    use_cothread = False
    _pva_server = None
    _spawned = None
    _published = ()
    _endpoints = None

    def do_init(self):
        self._start_pva_server()

    @Process.Publish
    def publish(self, published):
        # Administer endpoints
        self._published = published
        if self._pva_server:
            with self._lock:
                # Delete blocks we no longer have
                for block_name in self._endpoints:
                    if block_name not in published:
                        # TODO: delete endpoint here when we can
                        pass
                # Add new blocks
                for block_name in published:
                    if block_name not in self._endpoints:
                        self._add_new_pva_channel(block_name)

    def _add_new_pva_channel(self, block_name):
        """Create a new PVA endpoint for the block name

        Args:
            block_name (str): The name of the block to create the PVA endpoint
        """
        controller = self.process.get_controller(block_name)

        def _get(pv_request):
            try:
                return PvaGetImplementation(block_name, controller, pv_request)
            except Exception:
                self.log_exception("Error doing Get")

        def _put(pv_request):
            try:
                return PvaPutImplementation(block_name, controller, pv_request)
            except Exception:
                self.log_exception("Error doing Put")

        def _rpc(pv_request):
            try:
                rpc = PvaRpcImplementation(block_name, controller, pv_request)
                return rpc.execute
            except Exception:
                self.log_exception("Error doing Rpc")

        def _monitor(pv_request):
            try:
                return PvaMonitorImplementation(
                    block_name, controller, pv_request)
            except Exception:
                self.log_exception("Error doing Monitor")

        endpoint = pvaccess.Endpoint()
        endpoint.registerEndpointGet(_get)
        endpoint.registerEndpointPut(_put)
        # TODO: There is no way to eliminate dead RPC connections
        endpoint.registerEndpointRPC(_rpc)
        # TODO: There is no way to eliminate dead monitors
        # TODO: Monitors do not support deltas
        endpoint.registerEndpointMonitor(_monitor)
        self._pva_server.registerEndpoint(block_name, endpoint)
        self._endpoints[block_name] = endpoint

    def _start_pva_server(self):
        if self._pva_server is None:
            self._pva_server = pvaccess.PvaServer()
            # {block_name: Endpoint}
            self._endpoints = {}
            for block_name in self._published:
                self._add_new_pva_channel(block_name)
            self._spawned = self.spawn(self._pva_server.startListener)

    def _stop_pva_server(self):
        if self._pva_server is not None:
            self._pva_server.shutdown()
            self._pva_server = None
            self._spawned.wait(10)


class PvaImplementation(Loggable):
    def __init__(self, block_name, controller, request):
        self.set_logger_name("%s(%s)" % (type(self).__name__, block_name))
        self._block_name = block_name
        self._controller = controller
        self._request = request

    def _dict_to_path_value(self, pv_request):
        value = pv_request.toDict()
        if "field" in value:
            value = value["field"]
        path = []
        while isinstance(value, dict) and len(value) == 1:
            endpoint = list(value)[0]
            value = value[endpoint]
            path.append(endpoint)
        return path, value

    def _request_response(self, request_cls, path, **kwargs):
        queue = Queue()
        request = request_cls(
            path=[self._block_name] + path, callback=queue.put, **kwargs)
        self._controller.handle_request(request)
        response = queue.get()
        if isinstance(response, Error):
            raise ResponseError(response.message)
        else:
            return response

    def _get_pv_structure(self, pv_request):
        # TODO: do we need to take this or should we use self._request?
        path, _ = self._dict_to_path_value(pv_request)
        response = self._request_response(Get, path)
        # We are expected to provide all the levels in the dict. E.g. if
        # asked to get ["block", "attr", "value"], we should provide
        # {"attr": {"value": 32}}
        response_dict = response.value
        for endpoint in reversed(path):
            response_dict = {endpoint: response_dict}
        pv_structure = dict_to_pv_object(response_dict)
        return pv_structure


class PvaGetImplementation(PvaImplementation):
    _pv_structure = None

    def getPVStructure(self):
        self.log_debug("getPVStructure")
        if self._pv_structure is None:
            self._pv_structure = self._get_pv_structure(self._request)
        return self._pv_structure

    def get(self):
        # No-op as getPvStructure gets values too
        self.log_debug("get")


class PvaPutImplementation(PvaGetImplementation):
    def put(self, put_request):
        self.log_debug("put %s", put_request.toDict())
        self.getPVStructure()
        try:
            path, value = self._dict_to_path_value(put_request)
            self._request_response(Put, path, value=value)
        except Exception:
            self.log_exception(
                "Exception while putting %s", put_request.toDict())


class PvaRpcImplementation(PvaImplementation):

    def _strip_tuples(self, item):
        if isinstance(item, dict):
            for k, v in item.items():
                item[k] = self._strip_tuples(v)
        elif isinstance(item, list):
            for i, v in enumerate(item):
                item[i] = self._strip_tuples(v)
        elif isinstance(item, tuple):
            # Just take the first element, for variant unions?
            item = self._strip_tuples(item[0])
        return item

    def execute(self, args):
        self.log_debug("execute")
        try:
            print "execute", args.toDict(True)
            print self._request["method"]
            self.log_debug("execute %s %s", self._request["method"], args.toDict())
            method_name = self._request["method"]
            path = [method_name]
            parameters = self._strip_tuples(args.toDict(True))
            response = self._request_response(Post, path, parameters=parameters)
            if response.value:
                pv_object = dict_to_pv_object(response.value)
            else:
                # We need to return something, otherwise we get a timeout...
                pv_object = dict_to_pv_object(dict(typeid=Map.typeid))
            self.log_debug("return %s", pv_object.toDict())
            return pv_object
        except Exception as e:
            self.log_exception("Error doing execute")
            error = Error(message=str(e)).to_dict()
            error.pop("id")
            return dict_to_pv_object(error)


class PvaMonitorImplementation(PvaGetImplementation):
    def __init__(self, block_name, controller, request):
        super(PvaMonitorImplementation, self).__init__(
            block_name, controller, request)
        self._mu = pvaccess.MonitorServiceUpdater()
        self.getPVStructure()
        self._do_update = False
        path, _ = self._dict_to_path_value(self._request)
        request = Subscribe(path=[self._block_name] + path, delta=True,
                            callback=self._on_response)
        self._controller.handle_request(request)

    def getUpdater(self):
        return self._mu

    def _on_response(self, delta):
        """Handle Delta response to Subscribe

        Args:
            delta (Delta): The response
        """
        for change in delta.changes:
            field_path = ".".join(
                self._dict_to_path_value(self._request)[0] + change[0])
            if field_path and self._pv_structure.hasField(field_path):
                new_value = value_for_pva_set(change[1])
                # Don't update on the first change if all is the same
                if not self._do_update:
                    if self._pv_structure[field_path] != new_value:
                        continue
                    else:
                        self._do_update = True
                self._pv_structure[field_path] = new_value
        if not self._do_update:
            # First update gave us not changes, but unconditionally update from
            # now on
            self._do_update = True
        else:
            self._mu.update()
