import os

from annotypes import Anno, add_call_types
from tornado.web import RedirectHandler, StaticFileHandler

from malcolm.core import APartName, Part, PartRegistrar

from ..hooks import ReportHandlersHook, UHandlerInfos
from ..infos import HandlerInfo

www_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "www"))


with Anno("Path to www directory to get files from"):
    APath = str


# Always serve index.html, no matter what the route
class IndexHandler(StaticFileHandler):
    @classmethod
    def get_absolute_path(cls, root, path):
        return super(IndexHandler, cls).get_absolute_path(root, "index.html")


class GuiServerPart(Part):
    """Static file server to be used as a fallback. Must be last part"""

    GuiHandler = IndexHandler

    def __init__(self, name: APartName = "gui", path: APath = www_dir) -> None:
        super().__init__(name)
        self.path = path

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(ReportHandlersHook, self.on_report_handlers)

    @add_call_types
    def on_report_handlers(self) -> UHandlerInfos:
        infos = [
            # Redirect / to /gui/
            HandlerInfo(r"/", RedirectHandler, url="/gui/"),
            # Serve index.html for /gui or /details
            HandlerInfo(r"/(gui|details).*", self.GuiHandler, path=self.path),
            # Anything else should be a static file handle
            HandlerInfo(r"/(.*)", StaticFileHandler, path=self.path),
        ]
        return infos
