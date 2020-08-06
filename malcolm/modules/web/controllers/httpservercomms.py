from typing import Optional

from annotypes import Anno, add_call_types
from cothread import cothread
from tornado.httpserver import HTTPServer
from tornado.web import Application

from malcolm.core import APublished, Part, ProcessPublishHook, TableMeta
from malcolm.modules import builtin

from ..hooks import ReportHandlersHook
from ..infos import HandlerInfo
from ..util import BlockTable, IOLoopHelper

with Anno("TCP port number to run up under"):
    APort = int


class HTTPServerComms(builtin.controllers.ServerComms):
    """A class for communication between browser and server"""

    def __init__(self, mri: builtin.controllers.AMri, port: APort = 8008) -> None:
        super().__init__(mri)
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._server_started = False
        self._application: Optional[Application] = None
        self.blocks = TableMeta.from_table(
            BlockTable, "List of local Blocks to serve up"
        ).create_attribute_model()
        self.field_registry.add_attribute_model("blocks", self.blocks)
        # Hooks
        self.register_hooked(ProcessPublishHook, self.publish)

    def do_init(self):
        super().do_init()
        part_info = self.run_hooks(
            ReportHandlersHook(part) for part in self.parts.values()
        )
        handler_infos = HandlerInfo.filter_values(part_info)
        handlers = []
        for handler_info in handler_infos:
            handlers.append(
                (handler_info.regexp, handler_info.request_class, handler_info.kwargs)
            )
        self._application = Application(handlers)
        self._server = HTTPServer(self._application)
        self._start_server()

    def _start_server(self):
        if not self._server_started:
            IOLoopHelper.call(self._server.listen, int(self.port))
            self._server_started = True

    def _stop_server(self):
        if self._server_started:
            IOLoopHelper.call(self._server.stop)
            self._server_started = False

    def do_disable(self):
        super().do_disable()
        self._stop_server()

    def do_reset(self):
        super().do_reset()
        self._start_server()

    @add_call_types
    def publish(self, published: APublished) -> None:
        rows = []
        assert self.process, "No attached process"
        for mri in published:
            label = self.process.block_view(mri).meta.label
            if not label:
                label = mri
            rows.append((mri, label))
        self.blocks.set_value(BlockTable.from_rows(rows))

    def update_request_received(
        self, part: Part, info: builtin.infos.RequestInfo
    ) -> None:
        if info.mri == ".":
            # This is for us
            controller = self
        else:
            assert self.process, "No attached process"
            controller = self.process.get_controller(info.mri)
        cothread.Callback(controller.handle_request, info.request)
