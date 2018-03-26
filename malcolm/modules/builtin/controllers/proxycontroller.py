from annotypes import Anno

from malcolm.core import Post, Subscribe, Put, Hook, Alarm, Unsubscribe, \
    Delta, Queue, ProcessStopHook, ProcessStartHook, deserialize_object, \
    Response, UnpublishedInfo, UUnpublishedInfos
from .basiccontroller import BasicController, AMri
from ..infos import HealthInfo

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
        self.update_health(self, HealthInfo(Alarm.invalid("Uninitialized")))
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

    def handle_request(self, request):
        # Forward Puts and Posts to the client_comms
        if isinstance(request, (Put, Post)):
            return self.client_comms.send_to_server(request)
        else:
            return super(ProxyController, self).handle_request(request)

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
        elif path[0] not in ("health", "meta"):
            # Update a child of the block
            assert len(change) == 2, \
                "Can't delete entries in Attributes or Methods"
            ob = self._block
            for p in path[:-1]:
                ob = ob[p]
            # special case attribute values and timeStamps
            if len(path) == 2 and path[-1] == "value":
                ob.set_value(change[1], set_alarm_ts=False)
            elif len(path) == 2 and path[-1] == "timeStamp":
                ob.set_ts(change[1])
            else:
                getattr(ob, "set_%s" % path[-1])(change[1])
        elif len(path) == 2 and path[:1] == ["health", "alarm"]:
            # If we got an alarm update for health
            assert len(change) == 2, "Can't delete health alarm"
            alarm = deserialize_object(change[1], Alarm)
            self.update_health(self, HealthInfo(alarm))
        else:
            raise ValueError("Bad change %s" % (change,))

    def _regenerate_block(self, d):
        for field in list(self._block):
            if field not in ("health", "meta"):
                self._block.remove_endpoint(field)
        for field, value in d.items():
            if field == "health":
                alarm = deserialize_object(value["alarm"], Alarm)
                self.update_health(self, HealthInfo(alarm))
            elif field == "meta":
                # TODO: set meta
                pass
            elif field != "typeid":
                # No need to set writeable_functions as the server will do it
                self._block.set_endpoint_data(field, value)
