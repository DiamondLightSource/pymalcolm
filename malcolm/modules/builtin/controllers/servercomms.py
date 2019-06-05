from malcolm.core import Part
from .statefulcontroller import StatefulController, AMri, ADescription
from ..infos import RequestInfo

# Pull re-used annotypes into our namespace in case we are subclassed
AMri = AMri
ADescription = ADescription


class ServerComms(StatefulController):
    """Abstract class for dealing with requests from outside"""
    def __init__(self, mri, description=""):
        # type: (AMri, ADescription) -> None
        super(ServerComms, self).__init__(mri, description)
        self.info_registry.add_reportable(
            RequestInfo, self.update_request_received)

    def update_request_received(self, _, info):
        # type: (Part, RequestInfo) -> None
        controller = self.process.get_controller(info.mri)
        # Don't wait for the server to actually handle the request, just return
        controller.handle_request(info.request)
