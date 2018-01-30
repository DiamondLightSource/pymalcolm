import os

from annotypes import Anno, add_call_types
from tornado.web import StaticFileHandler

from malcolm.core import Part, APartName, Hook
from ..hooks import ReportHandlersHook, UHandlerInfos
from ..infos import HandlerInfo


www_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "www"))


with Anno("Path to www directory to get files from"):
    APath = str


class FileServerPart(Part):
    """Static file server to be used as a fallback. Must be last part"""
    def __init__(self, name="FILESERVER", path=www_dir):
        # type: (APartName, APath) -> None
        super(FileServerPart, self).__init__(name)
        self.path = path

    def on_hook(self, hook):
        # type: (Hook) -> None
        if isinstance(hook, ReportHandlersHook):
            hook(self.report_handlers)
        else:
            super(FileServerPart, self).on_hook(hook)

    @add_call_types
    def report_handlers(self):
        # type: () -> UHandlerInfos
        info = HandlerInfo(
            r"/(.*)", StaticFileHandler, path=self.path,
            default_filename="index.html")
        return info
