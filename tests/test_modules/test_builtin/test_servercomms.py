import unittest

from malcolm.modules.builtin.controllers import ServerComms
from malcolm.core import Process, call_with_params


class TestServerComms(unittest.TestCase):

    def setUp(self):
        self.process = Process("proc")
        self.o = call_with_params(ServerComms, self.process, (),
                                  mri="mri")

    def test_init(self):
        assert self.o.mri == "mri"
