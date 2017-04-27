import unittest

from malcolm.modules.web.controllers import WebsocketClientComms
from malcolm.core import Process, call_with_params


class TestWebsocketClientComms(unittest.TestCase):

    def setUp(self):
        self.process = Process("proc")
        self.o = call_with_params(WebsocketClientComms, self.process, (),
                                  mri="mri")

    def test_init(self):
        assert self.o.params.hostname == "localhost"
        assert self.o.params.port == 8080
        assert self.o.params.connectTimeout == 5.0
        assert self.o.mri == "mri"
