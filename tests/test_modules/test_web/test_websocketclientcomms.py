import unittest

from malcolm.core import Process
from malcolm.modules.web.controllers import WebsocketClientComms


class TestWebsocketClientComms(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.o = WebsocketClientComms(mri="mri")

    def test_init(self):
        assert self.o.hostname == "localhost"
        assert self.o.port == 8008
        assert self.o.connect_timeout == 10.0
        assert self.o.mri == "mri"
