import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import unittest

from malcolm.controllers.builtin import ServerComms
from malcolm.core import Process, call_with_params


class TestServerComms(unittest.TestCase):

    def setUp(self):
        self.process = Process("proc")
        self.o = call_with_params(ServerComms, self.process, (),
                                  mri="mri")

    def test_init(self):
        assert self.o.mri == "mri"

if __name__ == "__main__":
    unittest.main(verbosity=2)