import os
import inspect

from tornado.options import options
from plop.viewer import IndexHandler, ViewFlatHandler

from malcolm.core import Part, APartName, PartRegistrar
from malcolm.modules import web
from malcolm.compat import get_profiler_dir


def plop_dir():
    return os.path.dirname(inspect.getfile(ViewFlatHandler))


class MalcolmIndexHandler(IndexHandler):
    def get_template_path(self):
        return os.path.join(plop_dir(), "templates")


class MalcolmViewHandler(ViewFlatHandler):
    def get_template_path(self):
        return os.path.join(plop_dir(), "templates")

    def embed_file(self, filename):
        with open(os.path.join(plop_dir(), "static", filename)) as f:
            return f.read()


class ProfilingViewerPart(Part):
    def __init__(self, name="profiles"):
        # type: (APartName) -> None
        super(ProfilingViewerPart, self).__init__(name)
        options.datadir = get_profiler_dir()

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(ProfilingViewerPart, self).setup(registrar)
        # Hooks
        registrar.hook(web.hooks.ReportHandlersHook, self.report_handlers)

    def report_handlers(self):
        infos = [
            web.infos.HandlerInfo("/%s" % self.name, MalcolmIndexHandler),
            web.infos.HandlerInfo("/view", MalcolmViewHandler)]
        return infos
