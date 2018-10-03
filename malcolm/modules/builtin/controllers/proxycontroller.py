from annotypes import Anno

from malcolm.core import Subscribe, Alarm, Unsubscribe, Delta, Queue, \
    ProcessStopHook, ProcessStartHook, deserialize_object, Response, \
    UnpublishedInfo, UUnpublishedInfos, serialize_object
from malcolm.core.models import NTScalar, BlockMeta
from .basiccontroller import BasicController, AMri


with Anno("Malcolm resource id of client comms"):
    AComms = str
with Anno("Whether to re-publish this block via server comms"):
    APublish = bool


class ProxyController(BasicController):
    """Sync a local block with a given remote block"""

    def __init__(self, mri, comms, publish=False):
        # type: (AMri, AComms, APublish) -> None
        super(ProxyController, self).__init__(mri)
        self.comms = comms
        self.publish = publish
        self.client_comms = None
        self.health.set_value(
            "Uninitialized", alarm=Alarm.invalid("Uninitialized"))
        self._response_queue = Queue()
        self._notify_response = True
        self._first_response_queue = Queue()
        # Hooks
        self.register_hooked(ProcessStartHook, self.init)
        self.register_hooked(ProcessStopHook, self.halt)

    def init(self):
        # type: () -> UUnpublishedInfos
        self.client_comms = self.process.get_controller(self.comms)
        subscribe = Subscribe(path=[self.mri], delta=True)
        subscribe.set_callback(self.handle_response)
        self.client_comms.send_to_server(subscribe)
        # Wait until connected
        self._first_response_queue.get(timeout=5)
        if not self.publish:
            return UnpublishedInfo(self.mri)

    def halt(self):
        unsubscribe = Unsubscribe()
        unsubscribe.set_callback(self.handle_response)
        self.client_comms.send_to_server(unsubscribe)

    def _handle_put(self, request):
        attribute = self._block[request.path[1]]
        request.value = serialize_object(attribute.meta.validate(request.value))
        self.client_comms.send_to_server(request)
        return []

    def _handle_post(self, request):
        method = self._block[request.path[1]]
        request.parameters = serialize_object(
            method.validate(request.parameters))
        self.client_comms.send_to_server(request)
        return []

    def handle_response(self, response):
        # type: (Response) -> None
        self._response_queue.put(response)
        self.spawn(self._handle_response)

    def _handle_response(self):
        with self.changes_squashed:
            if self._notify_response:
                self._first_response_queue.put(True)
                self._notify_response = False
            response = self._response_queue.get(timeout=0)  # type: Response
            if not isinstance(response, Delta):
                # Return or Error is the end of our subscription, log and ignore
                self.log.debug("Proxy got response %r", response)
                return
            for change in response.changes:
                try:
                    self._handle_change(change)
                except Exception:
                    self.log.exception("Error handling %s", response)
                    raise

    def _handle_change(self, change):
        path = change[0]
        if len(path) == 0:
            assert len(change) == 2, \
                "Can't delete root block with change %r" % (change,)
            self._regenerate_block(change[1])
        elif len(path) == 1 and path[0] not in ("health", "meta"):
            if len(change) == 1:
                # Delete a field
                self._block.remove_endpoint(path[1])
            else:
                # Change a single field of the block
                self._block.set_endpoint_data(path[1], change[1])
        else:
            self._block.apply_change(path, *change[1:])

    def _regenerate_block(self, d):
        for field in list(self._block):
            if field not in ("health", "meta"):
                self._block.remove_endpoint(field)
        for field, value in d.items():
            if field == "health":
                # Update health attribute
                value = deserialize_object(value)  # type: NTScalar
                self.health.set_value(
                    value=value.value,
                    alarm=value.alarm,
                    ts=value.timeStamp)
            elif field == "meta":
                value = deserialize_object(value)  # type: BlockMeta
                meta = self._block.meta  # type: BlockMeta
                for k in meta.call_types:
                    getattr(meta, "set_%s" % k)(value[k])
            elif field != "typeid":
                # No need to set writeable_functions as the server will do it
                self._block.set_endpoint_data(field, value)

