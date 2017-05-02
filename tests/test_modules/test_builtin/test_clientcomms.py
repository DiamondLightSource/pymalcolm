import unittest

from malcolm.core import Process, call_with_params
from malcolm.modules.builtin.controllers import ClientComms


class TestClientComms(unittest.TestCase):

    def setUp(self):
        self.process = Process("proc")
        self.o = call_with_params(ClientComms, self.process, (),
                                  mri="mri")

    def test_init(self):
        assert self.o.mri == "mri"

    def test_abstract(self):
        with self.assertRaises(NotImplementedError):
            self.o.send_to_server("anything")
