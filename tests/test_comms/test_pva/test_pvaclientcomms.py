import unittest
from mock import Mock, MagicMock, patch, call
from collections import OrderedDict

from malcolm.core.response import Error, Return, Delta
from malcolm.core.request import Post, Get
import pvaccess
pvaccess.Channel = MagicMock()

from malcolm.comms.pva.pvaclientcomms import PvaClientComms


class TestPVAClientComms(unittest.TestCase):

    def setUp(self):
        pvaccess.Channel = MagicMock()
        self.p = MagicMock()

    def test_init(self):
        self.PVA = PvaClientComms(self.p)
        self.assertEqual("PvaClientComms", self.PVA.name)
        self.assertEqual(self.p, self.PVA.process)

    def test_send_to_server(self):
        self.PVA = PvaClientComms(self.p)
        self.PVA.send_to_caller = MagicMock()
        request = Get(endpoint=["ep1", "ep2"])
        self.PVA.send_to_server(request)
        pvaccess.Channel.assert_called_once()
        self.PVA.send_to_caller.assert_called_once()

