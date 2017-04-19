from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application

from malcolm.modules.builtin.controllers.servercomms import ServerComms
from malcolm.core import Hook, method_also_takes, Process
from malcolm.modules.builtin.vmetas import NumberMeta
from malcolm.modules.web.infos import HandlerInfo


@method_also_takes(
    "port", NumberMeta("int32", "Port number to run up under"), 8080)
class HTTPServerComms(ServerComms):
    """A class for communication between browser and server"""
    _loop = None
    _server = None
    _spawned = None
    _application = None
    use_cothread = False

    ReportHandlers = Hook()
    """Called at init() to get all the handlers that should make the application

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
        loop (IOLoop): The IO loop that the server is running under

    Returns:
        [`HandlerInfo`] - any handlers and their regexps that need to form part
            of the tornado Application
    """

    Publish = Hook()
    """Called when a new block is added

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
        published (list): [mri] list of published Controller mris
    """

    def do_init(self):
        super(HTTPServerComms, self).do_init()
        self._loop = IOLoop()
        part_info = self.run_hook(
            self.ReportHandlers, self.create_part_contexts(), self._loop)
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
            self._server.listen(int(self.params.port))
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

    @Process.Publish
    def publish(self, published):
        if self._spawned:
            self.run_hook(self.Publish, self.create_part_contexts(), published)
