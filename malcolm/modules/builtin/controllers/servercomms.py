from malcolm.core import Part
from .statefulcontroller import StatefulController, AMri, ADescription, \
    AUseCothread
from ..infos import RequestInfo


class ServerComms(StatefulController):
    """Abstract class for dealing with requests from outside"""
    def __init__(self, mri, description="", use_cothread=True):
        # type: (AMri, ADescription, AUseCothread) -> None
        super(ServerComms, self).__init__(mri, description, use_cothread)
        self.info_registry.add_reportable(
            RequestInfo, self.update_request_received)

    def update_request_received(self, _, info):
        # type: (Part, RequestInfo) -> None
        controller = self.process.get_controller(info.mri)
        controller.handle_request(info.request).get()
