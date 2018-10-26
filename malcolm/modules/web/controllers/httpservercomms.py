from annotypes import Anno, add_call_types, TYPE_CHECKING
from cothread import cothread
from tornado.httpserver import HTTPServer
from tornado.web import Application

from malcolm.core import ProcessPublishHook, APublished, Part, StringArrayMeta, \
    Widget
from malcolm.modules import builtin
from ..infos import HandlerInfo
from ..hooks import ReportHandlersHook
from ..util import IOLoopHelper

if TYPE_CHECKING:
    from typing import List


with Anno("TCP port number to run up under"):
    APort = int


class HTTPServerComms(builtin.controllers.ServerComms):
    """A class for communication between browser and server"""

    def __init__(self, mri, port=8080):
        # type: (builtin.controllers.AMri, APort) -> None
        super(HTTPServerComms, self).__init__(mri)
        self.port = port
        self._server = None  # type: HTTPServer
        self._server_started = False
        self._application = None  # type: Application
        self._published = []  # type: List[str]
        self.blocks = StringArrayMeta(
            "List of local Blocks to serve up",
            tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model()
        self.field_registry.add_attribute_model("blocks", self.blocks)
        # Hooks
        self.register_hooked(ProcessPublishHook, self.publish)

    def do_init(self):
        super(HTTPServerComms, self).do_init()
        part_info = self.run_hooks(
            ReportHandlersHook(part)
            for part in self.parts.values())
        handler_infos = HandlerInfo.filter_values(part_info)
        handlers = []
        for handler_info in handler_infos:
            handlers.append((
                handler_info.regexp, handler_info.request_class,
                handler_info.kwargs))
        self._application = Application(handlers)
        self._server = HTTPServer(self._application)

    def _start_server(self):
        if not self._server_started:
            IOLoopHelper.call(self._server.listen, int(self.port))
            self._server_started = True

    def _stop_server(self):
        if self._server_started:
            IOLoopHelper.call(self._server.stop)
            self._server_started = False

    def do_disable(self):
        super(HTTPServerComms, self).do_disable()
        self._stop_server()

    def do_reset(self):
        super(HTTPServerComms, self).do_reset()
        self._start_server()

    @add_call_types
    def publish(self, published):
        # type: (APublished) -> None
        self._published = published
        self.blocks.set_value(published)
        # Start server if not already started
        self._start_server()

    def update_request_received(self, part, info):
        # type: (Part, builtin.infos.RequestInfo) -> None
        if info.mri == ".":
            # This is for us
            controller = self
        else:
            controller = self.process.get_controller(info.mri)
        cothread.Callback(controller.handle_request, info.request)
