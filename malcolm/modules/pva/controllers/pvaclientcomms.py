from p4p import Value
from p4p.nt import NTURI
from annotypes import TYPE_CHECKING

from malcolm.compat import maybe_import_cothread
from malcolm.modules.builtin.controllers import ClientComms
from malcolm.core import Request, Get, Put, Post, Subscribe, Update, Return, \
    Queue, deserialize_object, UnexpectedError, Unsubscribe, Delta, Response
from .pvaconvert import convert_value_to_dict, convert_to_type_tuple_value, Type


if TYPE_CHECKING:
    from typing import Dict, Tuple, Callable, Set


class PvaClientComms(ClientComms):
    """A class for a client to communicate with the server"""

    _monitors = None
    _send_queue = None
    _unsub_queue = None
    _pending_monitors = None
    _ctxt = None

    def do_init(self):
        super(PvaClientComms, self).do_init()
        cothread = maybe_import_cothread()
        if cothread:
            from p4p.client.cothread import Context, Subscription
        else:
            from p4p.client.thread import Context, Subscription
        self._ctxt = Context("pva", unwrap=False)
        self._monitors = {}  # type: Dict[Tuple[Callable, int], Subscription]
        self._pending_monitors = set()  # type: Set[Request]
        self._send_queue = Queue()
        # We can wait on this while there are _monitors
        self._unsub_queue = Queue()

    def do_disable(self):
        super(PvaClientComms, self).do_disable()
        while self._monitors:
            self._unsub_queue.get(timeout=1)
        self._ctxt.close()

    def send_to_server(self, request):
        """Dispatch a request to the server

        Args:
            request(Request): The message to pass to the server
        """
        self._send_queue.put(request)
        self.spawn(self._send_to_server, request)

    def _send_to_server(self, _):
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

    def _execute_get(self, request):
        path = ".".join(request.path[1:])
        value = self._ctxt.get(request.path[0], path)
        d = convert_value_to_dict(value)
        for k in request.path[1:]:
            d = d[k]
        response = Return(request.id, d)
        return response

    def _execute_put(self, request):
        path = ".".join(request.path[1:])
        typ, value = convert_to_type_tuple_value(request.value)
        if isinstance(typ, tuple):
            # Structure, make into a Value
            _, typeid, fields = typ
            value = Value(Type(fields, typeid), value)
            # TODO: this doesn't work yet...
        self._ctxt.put(request.path[0], {path: value}, path)
        response = Return(request.id)
        return response

    def _make_delta(self, request, value, d, v):
        # type: (Request, Value, Dict, Value) -> Response
        # If we wanted a delta, work out what changed
        changes = {}
        # What we should trim from each changed field
        trim = sum(len("." + x) for x in request.path[1:])
        for field in value.asSet():
            # Check each element to see if the root is changed
            fv = v
            fd = d
            fp = []
            for k in field[trim:].split("."):
                fp.append(k)
                if fv.changed(k):
                    # A root has changed, add it to the change set if
                    # not already on there and stop processing this
                    # change
                    tp = tuple(fp)
                    if tp not in changes:
                        changes[tp] = fd[k]
                    break
                fv = fv[k]
                fd = fd[k]
        # Make the delta
        changes = [[list(k), v] for k, v in changes.items()]
        response = Delta(request.id, changes=changes)
        return response

    def _execute_monitor(self, request):
        def callback(value=None):
            self.log.debug("Callback %s", value)
            d = convert_value_to_dict(value)
            v = value
            for k in request.path[1:]:
                d = d[k]
                v = v[k]
            if request.delta:
                try:
                    self._pending_monitors.remove(request)
                except KeyError:
                    # This is a subsequent monitor update
                    response = self._make_delta(request, value, d, v)
                else:
                    # This is the first monitor update
                    response = Delta(request.id, [[[], d]])
            else:
                # If we wanted an update, give the entire thing
                response = Update(request.id, d)
            request.callback(response)

        if request.delta:
            self._pending_monitors.add(request)
        m = self._ctxt.monitor(request.path[0], callback)
        self._monitors[request.generate_key()] = m

    def _execute_unsubscribe(self, request):
        monitor = self._monitors[request.generate_key()]
        monitor.close()
        # Don't pop until we have done the close, avoiding a race with
        # ctxt.close
        self._monitors.pop(request.generate_key())
        self._unsub_queue.put(None)
        response = Return(request.id)
        return response

    def _execute_rpc(self, request):
        typ, parameters = convert_to_type_tuple_value(request.parameters)
        uri = NTURI(typ[2])

        uri = uri.wrap(
            path=".".join(request.path),
            kws=parameters,
            scheme="pva"
        )
        value = self._ctxt.rpc(request.path[0], uri, timeout=None)
        d = convert_value_to_dict(value)
        response = Return(request.id, d)
        return response
