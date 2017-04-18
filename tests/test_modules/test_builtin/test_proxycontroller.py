import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import unittest
from mock import MagicMock

from malcolm.controllers.builtin import ProxyController
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

if __name__ == "__main__":
    unittest.main(verbosity=2)