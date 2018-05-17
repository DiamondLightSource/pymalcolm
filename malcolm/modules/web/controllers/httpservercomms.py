from annotypes import Anno, add_call_types
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application

from malcolm.core import Spawned, ProcessPublishHook, APublished
from malcolm.modules import builtin
from ..infos import HandlerInfo
from ..hooks import ReportHandlersHook, PublishHook


with Anno("TCP port number to run up under"):
    APort = int


class HTTPServerComms(builtin.controllers.ServerComms):
    """A class for communication between browser and server"""

    def __init__(self, mri, port=8080):
        # type: (builtin.controllers.AMri, APort) -> None
        super(HTTPServerComms, self).__init__(mri, use_cothread=False)
        self.port = port
        self._loop = None  # type: IOLoop
        self._server = None  # type: HTTPServer
        self._spawned = None  # type: Spawned
        self._application = None  # type: Application
        # Hooks
        self.register_hooked(ProcessPublishHook, self.publish)

    def do_init(self):
        super(HTTPServerComms, self).do_init()
        self._loop = IOLoop()
        part_info = self.run_hooks(
            ReportHandlersHook(part, self._loop)
            for part in self.parts.values())
        handler_infos = HandlerInfo.filter_values(part_info)
        handlers = []
        for handler_info in handler_infos:
            handlers.append((
                handler_info.regexp, handler_info.request_class,
                handler_info.kwargs))
        self._application = Application(handlers)
        self.start_io_loop()

    def start_io_loop(self):
        if self._spawned is None:
            self._server = HTTPServer(self._application)
            self._server.listen(int(self.port))
            self._spawned = self.spawn(self._loop.start)

    def stop_io_loop(self):
        if self._spawned:
            self._loop.add_callback(self._server.stop)
            self._loop.add_callback(self._loop.stop)
            self._spawned.wait(timeout=10)
            self._spawned = None

    def do_disable(self):
        super(HTTPServerComms, self).do_disable()
        self.stop_io_loop()

    def do_reset(self):
        super(HTTPServerComms, self).do_reset()
        self.start_io_loop()

    @add_call_types
    def publish(self, published):
        # type: (APublished) -> None
        if self._spawned:
            self.run_hooks(PublishHook(part, published)
                           for part in self.parts.values())
