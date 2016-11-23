import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock

from malcolm.core.response import Error, Return
from malcolm.core.request import Post, Get, Put, Subscribe
import pvaccess
import numpy as np

from malcolm.comms.pva.pvaclientcomms import PvaClientComms


class TestPVAClientComms(unittest.TestCase):

    def setUp(self):
        self.ch = MagicMock()
        self.ret_val = MagicMock()
        self.ch.get = MagicMock(return_value = self.ret_val)
        self.ch.subscribe = MagicMock()
        self.ch.startMonitor = MagicMock()
        pvaccess.Channel = MagicMock(return_value = self.ch)
        self.rpc = MagicMock()
        self.rpc.invoke = MagicMock(return_value = self.ret_val)
        pvaccess.RpcClient = MagicMock(return_value = self.rpc)
        self.p = MagicMock()
        pvaccess.PvObject = MagicMock()

    def test_init(self):
        self.PVA = PvaClientComms(self.p)
        self.assertEqual("PvaClientComms", self.PVA.name)
        self.assertEqual(self.p, self.PVA.process)

    def test_send_get_to_server(self):
        self.PVA = PvaClientComms(self.p)
        self.PVA.send_to_caller = MagicMock()
        request = Get(endpoint=["ep1", "ep2"])
        self.PVA.send_to_server(request)
        pvaccess.Channel.assert_called_once()
        self.ch.get.assert_called_once()
        self.PVA.send_to_caller.assert_called_once()
        self.PVA.send_to_caller.reset_mock()
        self.ret_val.toDict = MagicMock(return_value = {'typeid': 'test1'})
        self.PVA.send_to_server(request)
        self.assertIsInstance(self.PVA.send_to_caller.call_args[0][0], Return)
        self.PVA.send_to_caller.reset_mock()
        self.ret_val.toDict = MagicMock(return_value={'typeid': 'malcolm:core/Error:1.0'})
        self.PVA.send_to_server(request)
        self.assertIsInstance(self.PVA.send_to_caller.call_args[0][0], Error)

    def test_send_put_to_server(self):
        self.PVA = PvaClientComms(self.p)
        self.PVA.send_to_caller = MagicMock()
        request = Put(endpoint=["ep1", "ep2"], value="val1")
        self.PVA.send_to_server(request)
        pvaccess.Channel.assert_called_once()
        self.ch.put.assert_called_once()
        self.PVA.send_to_caller.assert_called_once()

    def test_send_post_to_server(self):
        self.PVA = PvaClientComms(self.p)
        self.PVA.send_to_caller = MagicMock()
        request = Post(endpoint=["ep1", "method1"], parameters={'arg1': np.int32(1)})
        self.PVA.send_to_server(request)
        pvaccess.RpcClient.assert_called_once()
        self.rpc.invoke.assert_called_once()
        self.PVA.send_to_caller.assert_called_once()
        self.PVA.send_to_caller.reset_mock()
        self.ret_val.toDict = MagicMock(return_value={'typeid': 'test1'})
        self.PVA.send_to_server(request)
        self.assertIsInstance(self.PVA.send_to_caller.call_args[0][0], Return)
        self.PVA.send_to_caller.reset_mock()
        self.ret_val.toDict = MagicMock(return_value={'typeid': 'malcolm:core/Error:1.0'})
        self.PVA.send_to_server(request)
        self.assertIsInstance(self.PVA.send_to_caller.call_args[0][0], Error)

    def test_send_subscribe_to_server(self):
        self.PVA = PvaClientComms(self.p)
        self.PVA.send_to_caller = MagicMock()
        request = Subscribe(endpoint=["ep1", "ep2"])
        request.set_id(1)
        self.PVA.send_to_server(request)
        pvaccess.Channel.assert_called_once()
        self.ch.subscribe.assert_called_once()
        self.ch.startMonitor.assert_called_once()
        mon = self.PVA._monitors[1]
        mon_val = MagicMock()
        mon_val.toDict = MagicMock(return_value={'typeid': 'malcolm:core/Error:1.0', 'message': 'test error'})
        self.PVA.send_to_caller.reset_mock()
        mon.monitor_update(mon_val)
        self.PVA.send_to_caller.assert_called_once()
        self.PVA.send_to_caller.reset_mock()
        mon_val = MagicMock()
        mon_val.toDict = MagicMock(return_value={'typeid': 'malcolm:core/Update:1.0'})
        mon.monitor_update(mon_val)
        self.PVA.send_to_caller.assert_called_once()

