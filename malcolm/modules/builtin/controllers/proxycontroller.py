import functools

from annotypes import Anno

from malcolm.core import (
    Alarm,
    Context,
    ProcessStartHook,
    UnpublishedInfo,
    UUnpublishedInfos,
)

from ..util import wait_for_stateful_block_init
from .basiccontroller import AMri, BasicController
from .clientcomms import ClientComms

with Anno("Malcolm resource id of client comms"):
    AComms = str
with Anno("Whether to re-publish this block via server comms"):
    APublish = bool

# Pull re-used annotypes into our namespace in case we are subclassed
AMri = AMri


class ProxyController(BasicController):
    """Sync a local block with a given remote block"""

    def __init__(self, mri: AMri, comms: AComms, publish: APublish = False) -> None:
        super(ProxyController, self).__init__(mri)
        self.comms = comms
        self.publish = publish
        self.client_comms = None
        self.health.set_value("Uninitialized", alarm=Alarm.invalid("Uninitialized"))
        # Hooks
        self.register_hooked(ProcessStartHook, self.init)

    def init(self) -> UUnpublishedInfos:
        self.client_comms: ClientComms = self.process.get_controller(self.comms)
        # Wait until connected
        context = Context(self.process)
        wait_for_stateful_block_init(context, self.comms)
        # Tell the client comms to sync our block for us
        self.client_comms.sync_proxy(self.mri, self._block)
        if not self.publish:
            return UnpublishedInfo(self.mri)

    def get_post_function(self, method_name):
        return functools.partial(self.client_comms.send_post, self.mri, method_name)

    def get_put_function(self, attribute_name):
        return functools.partial(self.client_comms.send_put, self.mri, attribute_name)

    def check_field_writeable(self, field):
        # Let the server do this
        pass

    def update_method_logs(
        self, method, took_value, took_ts, returned_value, returned_alarm
    ):
        # Let the server do this
        pass
