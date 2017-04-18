import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import unittest

from malcolm.controllers.builtin import ClientComms
from malcolm.core import Process, call_with_params


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

if __name__ == "__main__":
    unittest.main(verbosity=2)
