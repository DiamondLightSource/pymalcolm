import unittest
from mock import Mock, MagicMock, patch, call
from collections import OrderedDict

from malcolm.core.response import Error, Return, Delta
from malcolm.core.request import Post
import pvaccess
pvaccess.PvaServer = MagicMock()
pvaccess.Endpoint = MagicMock()
pvaccess.STRING = "STRING"
pvaccess.BOOLEAN = "BOOLEAN"
pvaccess.FLOAT = "FLOAT"
pvaccess.INT = "INT"
pvaccess.LONG = "LONG"

class PvTempObject(object):
    def __init__(self, dict_in, type):
        self._dict = dict_in
        self._type = type

    def __repr__(self):
        s = "<PvTempObject type=%s dict=%s>"%(self._type, str(self._dict))
        return s

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            for key in self._dict:
                if key in other._dict:
                    if self._dict[key] != other._dict[key]:
                        return False
                else:
                    return False
            return self._type == other._type
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def set(self, dict_in):
        self._dict = dict_in

pvaccess.PvObject = PvTempObject

from malcolm.comms.pva.pvaservercomms import PvaServerComms, PvaGetImplementation, PvaPutImplementation, PvaRpcImplementation, PvaEndpoint

class TestPVAServerComms(unittest.TestCase):

    def setUp(self):
        pvaccess.PvaServer = MagicMock()
        pvaccess.Endpoint = MagicMock()
        pvaccess.PvObject = PvTempObject
        self.p = MagicMock()

    @patch('malcolm.comms.pva.pvaservercomms.PvaRpcImplementation')
    def test_pva_endpoint(self, mock_rpc):
        pva_server_mock = MagicMock()
        server_mock = MagicMock()
        pvaccess.Endpoint.registerEndpointGet = MagicMock()
        pvaccess.Endpoint.registerEndpointPut = MagicMock()
        pvaccess.Endpoint.registerEndpointRPC = MagicMock()
        endpoint = PvaEndpoint("test.name", "test.block", pva_server_mock, server_mock)
        request = MagicMock()
        endpoint.get_callback(request)
        server_mock.get_request.assert_has_calls([call("test.block", request)])
        request = MagicMock()
        endpoint.rpc_callback(request)
        server_mock._get_unique_id.assert_called_once()
        server_mock.register_rpc.assert_called_once()
        server_mock.reset_mock()
        endpoint.put_callback(request)
        server_mock._get_unique_id.assert_called_once()
        server_mock.register_put.assert_called_once()
        server_mock.get_request.assert_has_calls([call("test.block", request)])

    def test_pva_get_implementation(self):
        server = MagicMock()
        server.get_request = MagicMock(return_value="test_return_1")
        request = MagicMock()
        pva = PvaGetImplementation("test.name", request, "test.block", server)
        server.get_request.assert_called_with("test.block", request)
        self.assertEqual(pva.getPVStructure(), "test_return_1")
        server.get_request = MagicMock(return_value="test_return_2")
        pva.get()
        server.get_request.assert_called_with("test.block", request)
        self.assertEqual(pva.getPVStructure(), "test_return_2")
        self.assertEqual(pva._name, "test.name")

    def test_pva_put_implementation(self):
        server = MagicMock()
        server.get_request = MagicMock(return_value="test_return_1")
        request = MagicMock()
        pva = PvaPutImplementation(1, "test.name", request, "test.block", server)
        self.assertEqual(pva._name, "test.name")
        server.get_request.assert_called_with("test.block", request)
        self.assertEqual(pva.getPVStructure(), "test_return_1")
        path = pva.dict_to_path({'p1': {'p2': {'p3': 'v3'}}})
        self.assertEqual(path, ['p1', 'p2', 'p3'])
        value = pva.dict_to_value({'p1': {'p2': {'p3': 'v3'}}})
        self.assertEqual(value, 'v3')
        pva._lock = MagicMock()
        pva._event = MagicMock()
        pva.check_lock()
        pva._lock.acquire.assert_has_calls([call(False)])
        pva.wait_for_reply()
        pva._event.wait.assert_called_once()
        response = MagicMock()
        pva.notify_reply(response)
        pva._event.set.assert_called_once()
        self.assertEqual(pva._response, response)
        server.get_request = MagicMock(return_value="test_return_2")
        pva.get()
        server.get_request.assert_called_with("test.block", request)
        self.assertEqual(pva.getPVStructure(), "test_return_2")
        pva.dict_to_path = MagicMock()
        pva.dict_to_value = MagicMock()
        pv = MagicMock()
        pva.put(pv)
        pva.dict_to_path.assert_called_once()
        pva.dict_to_value.assert_called_once()
        server.send_to_process.assert_called_once()
        server.remove_put.assert_called_once()

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

        pva._lock = MagicMock()
        pva.check_lock()
        pva._lock.acquire.assert_has_calls([call(False)])

        pva._event = MagicMock()
        pva.wait_for_reply()
        pva._event.wait.assert_called_once()

    def test_init(self):
        self.PVA = PvaServerComms(self.p)

        self.assertEqual("PvaServerComms", self.PVA.name)
        self.assertEqual(self.p, self.PVA.process)

    def test_unique_id(self):
        self.PVA = PvaServerComms(self.p)

        self.assertEqual(self.PVA._get_unique_id(), 2)
        self.assertEqual(self.PVA._get_unique_id(), 3)
        self.assertEqual(self.PVA._get_unique_id(), 4)
        self.assertEqual(self.PVA._get_unique_id(), 5)

    def test_update_block_list(self):
        self.PVA = PvaServerComms(self.p)
        self.PVA._add_new_pva_channel = MagicMock()

        self.PVA._cache = {"block1": 1, "block2": 2, "block3": 3}
        self.PVA._update_block_list()

        calls = [call("block3"), call("block2"), call("block1")]
        self.PVA._add_new_pva_channel.assert_has_calls(calls, any_order=True)

        self.PVA._add_new_pva_channel.reset_mock()
        self.PVA._cache = {"block1": 1, "block2": 2, "block3": 3, "block4": 4}
        self.PVA._update_block_list()
        calls = [call("block4")]
        self.PVA._add_new_pva_channel.assert_has_calls(calls, any_order=True)

    def test_update_cache(self):
        self.PVA = PvaServerComms(self.p)
        self.PVA._add_new_pva_channel = MagicMock()

        request = Delta(id_=1, changes=[[["block1"], 1], [["block2"], 2], [["block3"], 3]])
        self.PVA._update_cache(request)

        calls = [call("block1"), call("block2"), call("block3")]
        self.PVA._add_new_pva_channel.assert_has_calls(calls, any_order=True)

        self.assertEqual(self.PVA._cache, {"block1": 1, "block2": 2, "block3": 3})

    def test_send_to_client(self):
        self.PVA = PvaServerComms(self.p)
        self.PVA._update_cache = MagicMock()
        rpc_mock1 = MagicMock()
        rpc_mock2 = MagicMock()
        self.PVA._rpcs[1] = rpc_mock1
        self.PVA._rpcs[2] = rpc_mock2
        response1 = Return(id_=1)
        self.PVA.send_to_client(response1)
        rpc_mock1.notify_reply.assert_has_calls([call(response1)])
        response2 = Error(id_=2)
        self.PVA.send_to_client(response2)
        rpc_mock2.notify_reply.assert_has_calls([call(response2)])
        response3 = Delta(id_=3)
        self.PVA.send_to_client(response3)
        self.PVA._update_cache.assert_has_calls([call(response3)])

    def test_create_pva_server(self):
        self.PVA = PvaServerComms(self.p)
        pvaccess.PvaServer.reset_mock()
        self.PVA.create_pva_server()
        pvaccess.PvaServer.assert_called_once()

    def test_start_pva_server(self):
        self.PVA = PvaServerComms(self.p)
        self.PVA._server.startListener = MagicMock()
        self.PVA.start_pva_server()
        self.PVA._server.startListener.assert_called_once()

    def test_stop_pva_server(self):
        self.PVA = PvaServerComms(self.p)
        self.PVA._server.stop = MagicMock()
        self.PVA.stop_pva_server()
        self.PVA._server.stop.assert_called_once()

    @patch('malcolm.comms.pva.pvaservercomms.PvaEndpoint')
    def test_add_new_pva_channel(self, mock_endpoint):
        self.PVA = PvaServerComms(self.p)
        self.PVA._add_new_pva_channel("test.block")
        mock_endpoint.assert_called_with("PvaServerComms", "test.block", self.PVA._server, self.PVA)

    def test_register_rpc(self):
        self.PVA = PvaServerComms(self.p)
        self.rpc = MagicMock()
        self.PVA.register_rpc(1, self.rpc)
        self.assertEqual(self.PVA._rpcs, {1: self.rpc})

    def test_register_dead_rpc(self):
        self.PVA = PvaServerComms(self.p)
        self.PVA.register_dead_rpc(1)
        self.PVA.register_dead_rpc(2)
        self.assertEqual(self.PVA._dead_rpcs, [1, 2])

    def test_purge_rpcs(self):
        self.PVA = PvaServerComms(self.p)
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

    def test_cache_to_pvobject(self):
        self.PVA = PvaServerComms(self.p)
        self.PVA._cache["test.block"] = OrderedDict({"p1": OrderedDict({"p2": "val2", "typeid": "type2"}), "typeid": "type1"})
        object = self.PVA.cache_to_pvobject("test.block", [["p1", "p2"]])
        self.assertEqual(object, PvTempObject(OrderedDict({"p1": OrderedDict({"p2": "val2"})}), "type1"))

        self.PVA._cache["test.block"] = OrderedDict({"p1": [OrderedDict({"p2": 2, "typeid": "type2"}),
                                                            OrderedDict({"p3": "val3", "typeid": "type3"})],
                                                     "typeid": "type1"})
        object = self.PVA.cache_to_pvobject("test.block", [["p1"]])
        self.assertEqual(object, PvTempObject(OrderedDict({"p1": [OrderedDict({"p2": 2, "typeid": "type2"}),
                                                                  OrderedDict({"p3": "val3", "typeid": "type3"})]}),
                                                           "type1"))

    def test_dict_to_stucture(self):
        self.PVA = PvaServerComms(self.p)
        #val = self.PVA.dict_to_structure({"typeid": "type1", "level1": {"typeid": "type2", "level2": {"typeid": "type3", "item1": 1, "item2": "2", "item3": True}}})
        import sys
        if sys.version_info[0] < 3:
            val = self.PVA.dict_to_pv_object_structure(OrderedDict({"typeid": "type1",
                                                                    "val1": "1",
                                                                    "val2": 2,
                                                                    "val3": True,
                                                                    "val4": long(0),
                                                                    "val5": 0.5,
                                                                    "val6": ['', ''],
                                                                    "val7": [5, 1],
                                                                    "val8": [True, False],
                                                                    "val9": [long(0), long(1)],
                                                                    "val10": [0.2, 0.3],
                                                                    }))
            test_dict = OrderedDict()
            test_dict["val1"] = pvaccess.STRING
            test_dict["val2"] = pvaccess.INT
            test_dict["val3"] = pvaccess.BOOLEAN
            test_dict["val4"] = pvaccess.LONG
            test_dict["val5"] = pvaccess.FLOAT
            test_dict["val6"] = [pvaccess.STRING]
            test_dict["val7"] = [pvaccess.INT]
            test_dict["val8"] = [pvaccess.BOOLEAN]
            test_dict["val9"] = [pvaccess.LONG]
            test_dict["val10"] = [pvaccess.FLOAT]
            test_val = pvaccess.PvObject(test_dict, "type1")
            self.assertEquals(val, test_val)
        else:
            val = self.PVA.dict_to_pv_object_structure(OrderedDict({"typeid": "type1",
                                                                    "val1": "1",
                                                                    "val2": 2,
                                                                    "val3": True,
                                                                    "val5": 0.5,
                                                                    "val6": ['', ''],
                                                                    "val7": [5, 1],
                                                                    "val8": [True, False],
                                                                    "val10": [0.2, 0.3],
                                                                    }))
            test_dict = OrderedDict()
            test_dict["val1"] = pvaccess.STRING
            test_dict["val2"] = pvaccess.INT
            test_dict["val3"] = pvaccess.BOOLEAN
            test_dict["val5"] = pvaccess.FLOAT
            test_dict["val6"] = [pvaccess.STRING]
            test_dict["val7"] = [pvaccess.INT]
            test_dict["val8"] = [pvaccess.BOOLEAN]
            test_dict["val10"] = [pvaccess.FLOAT]
            test_val = pvaccess.PvObject(test_dict, "type1")
            self.assertEquals(val, test_val)

        # Test the variant union array type
        val = self.PVA.dict_to_pv_object_structure(OrderedDict({"union_array": [OrderedDict({"val1": 1}), OrderedDict({"val2": "2"})]}))
        test_dict = OrderedDict()
        test_dict["union_array"] = [({},)]
        test_val = pvaccess.PvObject(test_dict, "")
        self.assertEquals(val, test_val)

    def test_strip_type_id(self):
        self.PVA = PvaServerComms(self.p)
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
