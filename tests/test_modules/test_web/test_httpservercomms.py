import unittest

from malcolm.modules.web.controllers import HTTPServerComms
from malcolm.core import Process, call_with_params


class TestHTTPServerComms(unittest.TestCase):

    def setUp(self):
        self.process = Process("proc")
        self.o = call_with_params(HTTPServerComms, self.process, (),
                                  mri="mri")

    def test_init(self):
        assert self.o.params.port == 8080
        assert self.o.mri == "mri"
