import os
import inspect

from tornado.options import options
from plop.viewer import IndexHandler, ViewFlatHandler

from malcolm.core import Part, APartName, Hook
from malcolm.modules.web.hooks import ReportHandlersHook
from malcolm.modules.web.infos import HandlerInfo


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
    # This will be written by imalcolm
    profiledir = None

    def __init__(self, name="profiles"):
        # type: (APartName) -> None
        super(ProfilingViewerPart, self).__init__(name)
        options.datadir = self.profiledir
        # Hooks
        self.register_hooked(ReportHandlersHook, self.report_handlers)

    def report_handlers(self):
        infos = [
            HandlerInfo("/%s" % self.name, MalcolmIndexHandler),
            HandlerInfo("/view", MalcolmViewHandler)]
        return infos
