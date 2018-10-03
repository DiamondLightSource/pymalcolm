from annotypes import add_call_types, TYPE_CHECKING
from p4p import Value
from p4p.server import Server, DynamicProvider, ServerOperation

from malcolm.compat import maybe_import_cothread
from malcolm.core import Subscribe, Error, APublished, Controller, Delta, \
    Return, stringify_error, Response, Put, Post, Unsubscribe, \
    ProcessPublishHook, method_return_unpacked, Method, serialize_object
from malcolm.core.rlock import RLock
from malcolm.modules import builtin
from .pvaconvert import convert_dict_to_value, update_path, \
    convert_value_to_dict

if TYPE_CHECKING:
    from typing import Optional, Dict, List


cothread = maybe_import_cothread()

if cothread:
    from p4p.server.cothread import Handler, SharedPV
else:
    from p4p.server.thread import Handler, SharedPV


class BlockHandler(Handler):
    def __init__(self, controller, field=None):
        # type: (Controller, str) -> None
        self.controller = controller
        # Lock to control access to self.pv
        self._lock = RLock(controller.use_cothread)
        self.field = field
        self.pv = None  # type: Optional[SharedPV]
        self.value = None  # type: Value

    def rpc(self, pv, op):
        # type: (SharedPV, ServerOperation) -> None
        value = op.value()
        if value.getID() == "epics:nt/NTURI:1.0":
            # We got an NTURI, get path from path and parameters from query
            assert value.scheme == "pva", \
                "Can only handle NTURI with scheme=pva"
            prefix = self.controller.mri + "."
            assert value.path.startswith(prefix), \
                "NTURI path '%s' doesn't start with '%s'" % (value.path, prefix)
            method = value.path[len(prefix):]
            parameters = convert_value_to_dict(value.query)
        else:
            # We got something else, take path from pvRequest method and our mri
            # and parameters from the full value
            if self.field is not None:
                # We already know the method name
                method = self.field
            else:
                # Get the path and string "value" from the put value
                method = op.pvRequest().get("method")
                assert method, "No 'method' in pvRequest:\n%s" % op.pvRequest()
            parameters = convert_value_to_dict(value)
        path = [self.controller.mri, method]
        view = self.controller.make_view()[method]
        assert isinstance(view, Method), \
            "%s.%s is not a Method so cannot do RPC" % tuple(path)
        add_wrapper = method_return_unpacked() in view.tags

        post = Post(path=path, parameters=parameters)

        def handle_post_response(response):
            # type: (Response) -> None
            if isinstance(response, Return):
                if add_wrapper:
                    # Method gave us return unpacked (bare string or other type)
                    # so we must wrap it in a structure to send it
                    ret = {"return": response.value}
                else:
                    ret = response.value
                serialized = serialize_object(ret)
                v = convert_dict_to_value(serialized)
                self.controller.log.debug("Calling op.done with %s", v)
                op.done(v)
            else:
                if isinstance(response, Error):
                    message = stringify_error(response.message)
                else:
                    message = "BadResponse: %s" % response.to_dict()
                op.done(error=message)

        post.set_callback(handle_post_response)
        self.controller.handle_request(post).get()

    def put(self, pv, op):
        # type: (SharedPV, ServerOperation) -> None
        path = [self.controller.mri]
        changed_set = op.value().changedSet()
        assert len(changed_set) == 1, \
            "Can only do a Put to a single field, got %s" % list(changed_set)
        changed = list(changed_set)[0]
        if self.field is not None:
            # Only accept a Put to "value"
            assert changed == "value", \
                "Can only put to value of %s.%s, not %s" % (
                    self.controller.mri, self.field, changed)
            path += [self.field, "value"]
            op_value = op.value()
        else:
            # Get the path and string "value" from the put value
            split = changed.split(".")
            assert len(split) == 2 and split[1] == "value", \
                "Can only put to value of %s.%s, not %s" % (
                    self.controller.mri, split[0], split[1])
            path += list(split)
            op_value = op.value()[split[0]]
        value = convert_value_to_dict(op_value)["value"]
        put = Put(path=path, value=value)

        def handle_put_response(response):
            # type: (Response) -> None
            if isinstance(response, Return):
                op.done()
            else:
                if isinstance(response, Error):
                    message = stringify_error(response.message)
                else:
                    message = "BadResponse: %s" % response.to_dict()
                op.done(error=message)

        put.set_callback(handle_put_response)
        self.controller.handle_request(put).get()

    def handle(self, response):
        # type: (Response) -> None
        # Called from whatever thread the child block could be in, so
        # must already be a good thread to take the lock
        with self._lock:
            if self.pv and isinstance(response, Delta):
                # We got a delta, create or update value and notify
                if not self.pv.isOpen():
                    # Open it with the value
                    # TODO: at the moment this fires because we didn't close
                    # and wait for unsubscribe at tearDown
                    self._create_initial_value(response)
                else:
                    # Update it with values
                    self._update_value(response)
            elif self.pv and self.pv.isOpen():
                # We got a return or error, close the connection to clients
                self.pv.close()
                self.pv = None

    def _create_initial_value(self, delta):
        # type: (Delta) -> None
        # Called with the lock taken
        assert len(delta.changes) == 1 and len(delta.changes[0]) == 2 and \
            delta.changes[0][0] == [], "Expected root update, got %s" % (
                delta.changes,)
        self.value = convert_dict_to_value(delta.changes[0][1])
        self.pv.open(self.value)

    def _update_value(self, delta):
        # type: (Delta) -> None
        # Called with the lock taken
        self.value.unmark()
        for change in delta.changes:
            if len(change) == 1 or change[0] == []:
                # This is a delete or update of the root, can't do this in pva,
                # so force a reconnect
                self.onLastDisconnect(self.pv)
            else:
                # Path will have at least one element
                path, update = change
                # TODO: try catch with disconnect here, reopen with new value
                update_path(self.value, path, update)
        self.pv.post(self.value)

    # Need camelCase as called by p4p Server
    # noinspection PyPep8Naming
    def onFirstConnect(self, pv):
        # type: (SharedPV) -> None
        # Called from pvAccess thread, so spawn in the right (co)thread
        self.controller.spawn(self._on_first_connect, pv).get(timeout=1)

    def _on_first_connect(self, pv):
        # type: (SharedPV) -> None
        # Store the PV, but don't open it now, let the first Delta do this
        with self._lock:
            self.pv = pv
        path = [self.controller.mri]
        if self.field is not None:
            path.append(self.field)
        request = Subscribe(path=path, delta=True)
        request.set_callback(self.handle)
        # No need to wait for first update here
        self.controller.handle_request(request)

    # Need camelCase as called by p4p Server
    # noinspection PyPep8Naming
    def onLastDisconnect(self, pv):
        # type: (SharedPV) -> None
        # Called from pvAccess thread, so spawn in the right (co)thread
        self.controller.spawn(self._on_last_disconnect, pv).get(timeout=1)

    def _on_last_disconnect(self, pv):
        # type: (SharedPV) -> None
        # No-one listening, unsubscribe
        with self._lock:
            self.pv.close()
            self.pv = None
        request = Unsubscribe()
        request.set_callback(self.handle)
        self.controller.handle_request(request).get(timeout=1)


class PvaServerComms(builtin.controllers.ServerComms):
    """A class for communication between pva client and server"""

    def __init__(self, mri):
        # type: (builtin.controllers.AMri) -> None
        super(PvaServerComms, self).__init__(mri, use_cothread=True)
        self._pva_server = None
        self._provider = None
        self._published = ()
        self._pvs = {}  # type: Dict[str, List[SharedPV]]
        # Hooks
        self.register_hooked(ProcessPublishHook, self.publish)

    # Need camelCase as called by p4p Server
    # noinspection PyPep8Naming
    def testChannel(self, channel_name):
        # type: (str) -> bool
        if channel_name in self._published:
            # Someone is asking for a Block
            return True
        elif "." in channel_name:
            # Someone is asking for the field of a Block
            mri, field = channel_name.rsplit(".", 1)
            return mri in self._published
        else:
            # We don't have it
            return False

    # Need camelCase as called by p4p Server
    # noinspection PyPep8Naming
    def makeChannel(self, channel_name, src):
        # type: (str, str) -> SharedPV
        return self.spawn(self._makeChannel, channel_name, src).get(timeout=1)

    def _makeChannel(self, channel_name, src):
        # type: (str, str) -> SharedPV
        self.log.debug("Making PV %s for %s", channel_name, src)
        if channel_name in self._published:
            # Someone is asking for a Block
            mri = channel_name
            field = None
        elif "." in channel_name:
            # Someone is asking for the field of a Block
            mri, field = channel_name.rsplit(".", 1)
        else:
            raise NameError("Bad channel %s" % channel_name)
        controller = self.process.get_controller(mri)
        handler = BlockHandler(controller, field)
        # We want any client passing a pvRequest field() to ONLY receive that
        # field. The default behaviour of p4p is to send a masked version of
        # the full structure. The mapperMode option allows us to tell p4p to
        # send a slice instead
        # https://github.com/mdavidsaver/pvDataCPP/blob/master/src/copy/pv/createRequest.h#L76
        pv = SharedPV(handler=handler, options={'mapperMode': 'Slice'})
        self._pvs.setdefault(mri, []).append(pv)
        return pv

    def do_init(self):
        super(PvaServerComms, self).do_init()
        if self._pva_server is None:
            self.log.info("Starting PVA server")
            self._provider = DynamicProvider("PvaServerComms", self)
            self._pva_server = Server(providers=[self._provider])
            self.log.info("Started PVA server")

    def do_disable(self):
        super(PvaServerComms, self).do_disable()
        if self._pva_server is not None:
            self.log.info("Stopping PVA server")
            # Stop the server
            self._pva_server.stop()
            # Disconnect everyone
            self.disconnect_pv_clients(list(self._pvs))
            # Get rid of the server reference so we can't stop again
            self._pva_server = None
            self.log.info("Stopped PVA server")

    @add_call_types
    def publish(self, published):
        # type: (APublished) -> None
        self._published = published
        if self._pva_server:
            with self._lock:
                mris = [mri for mri in self._pvs if mri not in published]
                # Delete blocks we no longer have
                self.disconnect_pv_clients(mris)

    def disconnect_pv_clients(self, mris):
        # type: (List[str]) -> None
        """Disconnect anyone listening to any of the given mris"""
        for mri in mris:
            for pv in self._pvs.pop(mri, ()):
                # Close pv with force destroy on, this will call
                # onLastDisconnect
                pv.close(True)

