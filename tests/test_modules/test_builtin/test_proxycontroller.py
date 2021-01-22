import unittest

from mock import MagicMock

from malcolm.core import Process
from malcolm.modules.builtin.controllers import ProxyController


class TestProxyController(unittest.TestCase):
    def setUp(self):
        self.process = Process("proc")
        self.comms = MagicMock()
        self.comms.mri = "comms"
        self.process.add_controller(self.comms)
        self.o = ProxyController(mri="mri", comms="comms")
        self.process.add_controller(self.o)

    def test_init(self):
        assert self.o.mri == "mri"
        assert self.o.comms == "comms"
        assert self.o.client_comms is None
