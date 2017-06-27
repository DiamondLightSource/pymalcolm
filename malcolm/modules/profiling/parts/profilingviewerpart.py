import os
import inspect

from tornado.options import options
from plop.viewer import IndexHandler, ViewFlatHandler

from malcolm.core import method_takes, Part
from malcolm.modules.builtin.vmetas import StringMeta
from malcolm.modules.web.controllers import HTTPServerComms
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


@method_takes(
    "name", StringMeta("Name of the Part within the controller"), "profiles")
class ProfilingViewerPart(Part):
    # This will be written by imalcolm
    profiledir = None

    def __init__(self, params):
        self.params = params
        options.datadir = self.profiledir
        super(ProfilingViewerPart, self).__init__(params.name)

    @HTTPServerComms.ReportHandlers
    def report_handlers(self, context, loop):
        infos = [
            HandlerInfo("/%s" % self.params.name, MalcolmIndexHandler),
            HandlerInfo("/view", MalcolmViewHandler)]
        return infos
