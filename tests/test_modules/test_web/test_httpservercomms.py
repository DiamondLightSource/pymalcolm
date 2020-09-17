import unittest

from malcolm.modules.web.controllers import HTTPServerComms


class TestHTTPServerComms(unittest.TestCase):
    def setUp(self):
        self.o = HTTPServerComms(mri="mri")

    def test_init(self):
        assert self.o.port == 8008
        assert self.o.mri == "mri"
