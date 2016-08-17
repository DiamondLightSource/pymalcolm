import unittest
from mock import Mock, MagicMock, patch, call
from collections import OrderedDict

import sys
sys.modules['pvaccess'] = MagicMock()

from malcolm.core.response import Return, Delta
from malcolm.core.request import Post
import pvaccess
pvaccess.PvaServer = MagicMock()
pvaccess.Endpoint = MagicMock()
pvaccess.STRING = "STRING"
pvaccess.BOOLEAN = "BOOLEAN"
pvaccess.FLOAT = "FLOAT"
pvaccess.INT = "INT"


class PvTempObject(object):
    def __init__(self, dict_in, type):
        self._dict = dict_in
        self._type = type

    def __repr__(self):
        s = "<PvTempObject type=%s dict=%s>"%(self._type, str(self._dict))
        return s

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

pvaccess.PvObject = PvTempObject
from malcolm.comms.pva.pvaservercomms import PvaServerComms, PvaGetImplementation, PvaRpcImplementation, PvaEndpoint

class TestPVAServerComms(unittest.TestCase):

    def setUp(self):
        pvaccess.PvaServer = MagicMock()
        pvaccess.Endpoint = MagicMock()
        pvaccess.PvObject = PvTempObject
        self.p = MagicMock()

    def test_pva_endpoint(self):
        pva_server_mock = MagicMock()
        server_mock = MagicMock()
        endpoint = PvaEndpoint("test.name", "test.block", pva_server_mock, server_mock)
        calls = [call(endpoint.get_callback), call(endpoint.get_callback)]
        #endpoint._add_new_pva_channel.assert_has_calls(calls)

    def test_pva_get_implementation(self):
        pva = PvaGetImplementation("test.name", self.p)
        self.assertEqual(pva.getPVStructure(), self.p)
        self.assertEqual(pva._name, "test.name")

    def test_pva_rpc_implementation(self):
        self.p = MagicMock()
        self.p = MagicMock()
        pva = PvaRpcImplementation(1, self.p, "test.block", "test.method")
        self.assertEqual(pva._id, 1)
        self.assertEqual(pva._block, "test.block")
        self.assertEqual(pva._method, "test.method")
        self.assertEqual(pva._server, self.p)

        response = Return(id_=2, value="test.value")
        pva.notify_reply(response)
        self.pv = MagicMock()
        pva.execute(self.pv)
        self.p.process.q.put.assert_called_once()
        self.pv.toDict.assert_called_once()

    def test_init(self):
        self.PVA = PvaServerComms("TestPva", self.p)

        self.assertEqual("TestPva", self.PVA.name)
        self.assertEqual(self.p, self.PVA.process)

    def test_unique_id(self):
        self.PVA = PvaServerComms("TestPva", self.p)

        self.assertEqual(self.PVA._get_unique_id(), 2)
        self.assertEqual(self.PVA._get_unique_id(), 3)
        self.assertEqual(self.PVA._get_unique_id(), 4)
        self.assertEqual(self.PVA._get_unique_id(), 5)

    def test_update_block_list(self):
        self.PVA = PvaServerComms("TestPva", self.p)
        self.PVA._add_new_pva_channel = MagicMock()

        self.PVA._cache = {"block1": 1, "block2": 2, "block3": 3}
        self.PVA._update_block_list()

        calls = [call("block3"), call("block2"), call("block1")]
        self.PVA._add_new_pva_channel.assert_has_calls(calls)

        self.PVA._add_new_pva_channel.reset_mock()
        self.PVA._cache = {"block1": 1, "block2": 2, "block3": 3, "block4": 4}
        self.PVA._update_block_list()
        calls = [call("block4")]
        self.PVA._add_new_pva_channel.assert_has_calls(calls)

    def test_update_cache(self):
        self.PVA = PvaServerComms("TestPva", self.p)
        self.PVA._add_new_pva_channel = MagicMock()

        request = Delta(id_=1, changes=[[["block1"], 1], [["block2"], 2], [["block3"], 3]])
        self.PVA._update_cache(request)

        calls = [call("block1"), call("block2"), call("block3")]
        self.PVA._add_new_pva_channel.assert_has_calls(calls)

        self.assertEqual(self.PVA._cache, {"block1": 1, "block2": 2, "block3": 3})

    @patch('malcolm.comms.pva.pvaservercomms.PvaEndpoint')
    def test_add_new_pva_channel(self, mock_endpoint):
        self.PVA = PvaServerComms("TestPva", self.p)
        self.PVA._add_new_pva_channel("test.block")
        mock_endpoint.assert_called_with("TestPva", "test.block", self.PVA._server, self.PVA)

    def test_register_rpc(self):
        self.PVA = PvaServerComms("TestPva", self.p)
        self.rpc = MagicMock()
        self.PVA.register_rpc(1, self.rpc)
        self.assertEqual(self.PVA._rpcs, {1: self.rpc})

    def test_register_dead_rpc(self):
        self.PVA = PvaServerComms("TestPva", self.p)
        self.PVA.register_dead_rpc(1)
        self.PVA.register_dead_rpc(2)
        self.assertEqual(self.PVA._dead_rpcs, [1, 2])

    def test_purge_rpcs(self):
        self.PVA = PvaServerComms("TestPva", self.p)
        self.rpc1 = MagicMock()
        self.rpc2 = MagicMock()
        self.PVA.register_rpc(1, self.rpc1)
        self.PVA.register_rpc(2, self.rpc2)
        self.assertEqual(self.PVA._rpcs, {1: self.rpc1, 2: self.rpc2})
        self.PVA.register_dead_rpc(1)
        self.assertEqual(self.PVA._dead_rpcs, [1])
        self.PVA.purge_rpcs()
        self.assertEqual(self.PVA._rpcs, {2: self.rpc2})
        self.assertEqual(self.PVA._dead_rpcs, [])

    def test_dict_to_stucture(self):
        self.PVA = PvaServerComms("TestPva", self.p)
        #val = self.PVA.dict_to_structure({"typeid": "type1", "level1": {"typeid": "type2", "level2": {"typeid": "type3", "item1": 1, "item2": "2", "item3": True}}})
        val = self.PVA.dict_to_structure(OrderedDict({"typeid": "type1", "val1": "1", "val2": 2, "val3": True}))
        test_dict = OrderedDict()
        test_dict["val3"] = pvaccess.BOOLEAN
        test_dict["val1"] = pvaccess.STRING
        test_dict["val2"] = pvaccess.INT
        test_val = pvaccess.PvObject(test_dict, "type1")
        self.assertEquals(val, test_val)

    def test_strip_type_id(self):
        self.PVA = PvaServerComms("TestPva", self.p)
        #val = self.PVA.dict_to_structure({"typeid": "type1", "level1": {"typeid": "type2", "level2": {"typeid": "type3", "item1": 1, "item2": "2", "item3": True}}})
        val = self.PVA.strip_type_id(OrderedDict({"typeid": "type1", "val1": "1"}))
        self.assertEquals(val, OrderedDict({"val1": "1"}))


#    def test_start(self):
#        self.PVA = PvaServerComms("TestPva", self.p)
#        self.PVA.start()
#
#        self.assertEqual([call(self.PVA.send_loop), call(self.PVA.start)],
#                         self.p.spawn.call_args_list)

#    @patch('malcolm.comms.pva.pvaservercomms.IOLoop')
#    def test_stop(self, ioloop_mock):
#        loop_mock = MagicMock()
#        ioloop_mock.current.return_value = loop_mock
#        self.p.spawn = MagicMock()
#
#        self.PVA = PvaServerComms("TestPva", self.p)
#        self.PVA.start()
#        self.PVA.stop()
#
#        self.assertEqual([call(self.PVA.loop.stop)],
#                loop_mock.add_callback.call_args_list)
#        self.p.spawn.return_value.wait.assert_not_called()

#    @patch('malcolm.comms.pva.pvaservercomms.IOLoop')
#    def test_wait(self, ioloop_mock):
#        spawnable_mocks = [MagicMock(), MagicMock()]
#        timeout = MagicMock()
#        self.p.spawn = MagicMock(side_effect=spawnable_mocks)
#
#        self.PVA = PvaServerComms("TestPva", self.p)
#        self.PVA.start()
#        self.PVA.wait(timeout)
#
#        spawnable_mocks[0].wait.assert_called_once_with(timeout=timeout)
#        spawnable_mocks[1].wait.assert_called_once_with(timeout=timeout)

#    @patch('malcolm.comms.websocket.websocketservercomms.Serializable')
#    @patch('malcolm.comms.websocket.websocketservercomms.json')
#    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
#    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
#    def test_MWSH_on_message(self, _, _1, json_mock, serializable_mock):
#        self.WS = WebsocketServerComms("TestWebSocket", self.p, 1)
#
#        message_dict = dict(name="TestMessage")
#        json_mock.loads.return_value = message_dict
#
#        request = MagicMock()
#        request.context = self.WS.server.request_callback.handlers[0][1][0].handler_class
#        serializable_mock.from_dict.return_value = request
#
#        m = MagicMock()
#        MWSH = MalcolmWebSocketHandler(m, m)
#        self.WS.server.request_callback.handlers[0][1][0].handler_class.on_message(
#            MWSH, "TestMessage")
#
#        json_mock.loads.assert_called_once_with("TestMessage",
#                                                object_pairs_hook=OrderedDict)
#        serializable_mock.from_dict.assert_called_once_with(message_dict)
#        self.p.q.put.assert_called_once_with(request)

#    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer')
#    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
#    def test_on_request_with_process_name(self, _, _2):
#        self.WS = WebsocketServerComms("ws", self.p, 1)
#        request = MagicMock(fields=dict(endpoint="anything"), endpoint=[".", "blocks"])
#        self.WS.on_request(request)
#        self.p.q.put.assert_called_once_with(request)
#        self.assertEqual(request.endpoint, [self.p.name, "blocks"])

#    @patch('malcolm.comms.websocket.websocketservercomms.json')
#    @patch('malcolm.comms.websocket.websocketservercomms.HTTPServer.listen')
#    @patch('malcolm.comms.websocket.websocketservercomms.IOLoop')
#    def test_send_to_client(self, _, _2, json_mock):
#        self.WS = WebsocketServerComms("TestWebSocket", self.p, 1)
#
#        response_mock = MagicMock()
#        self.WS.send_to_client(response_mock)
#
#        json_mock.dumps.assert_called_once_with(response_mock.to_dict())
#        response_mock.context.write_message.assert_called_once_with(
#            json_mock.dumps())

if __name__ == "__main__":
    unittest.main(verbosity=2)
