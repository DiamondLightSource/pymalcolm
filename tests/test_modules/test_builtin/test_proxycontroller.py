import unittest
from mock import MagicMock

from malcolm.modules.builtin.controllers import ProxyController
from malcolm.core import Process, call_with_params


class TestProxyController(unittest.TestCase):

    def setUp(self):
        self.process = Process("proc")
        self.comms = MagicMock()
        self.process.add_controller("comms", self.comms)
        self.o = call_with_params(ProxyController, self.process, (),
                                  mri="mri", comms="comms")

    def test_init(self):
        assert self.o.mri == "mri"
        assert self.o.params.comms == "comms"
        assert self.o.client_comms == self.comms
