import inspect
import os

from plop.viewer import IndexHandler, ViewFlatHandler
from tornado.options import options

from malcolm.compat import get_profiler_dir
from malcolm.core import APartName, Part, PartRegistrar
from malcolm.modules import web


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
    def __init__(self, name: APartName = "profiles") -> None:
        super().__init__(name)
        options.datadir = get_profiler_dir()

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(web.hooks.ReportHandlersHook, self.on_report_handlers)

    def on_report_handlers(self):
        infos = [
            web.infos.HandlerInfo("/%s" % self.name, MalcolmIndexHandler),
            web.infos.HandlerInfo("/view", MalcolmViewHandler),
        ]
        return infos
