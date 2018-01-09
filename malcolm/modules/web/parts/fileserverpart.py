import os

from tornado.web import StaticFileHandler

from malcolm.core import method_takes, Part
from malcolm.core.vmetas import StringMeta
from malcolm.modules.web.controllers import HTTPServerComms
from malcolm.modules.web.infos import HandlerInfo


www_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "www"))


@method_takes(
    "path", StringMeta("Path to www directory to get files from"), www_dir)
class FileServerPart(Part):
    """Static file server to be used as a fallback. Must be last part"""
    def __init__(self, params):
        self.params = params
        super(FileServerPart, self).__init__("FILESERVER")

    @HTTPServerComms.ReportHandlers
    def report_handlers(self, context, loop):
        info = HandlerInfo(
            r"/(.*)", StaticFileHandler, path=self.params.path,
            default_filename="index.html")
        return [info]
