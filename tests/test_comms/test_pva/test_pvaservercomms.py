import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock, patch, call
from collections import OrderedDict

from malcolm.core.response import Error, Return, Delta, Update
from malcolm.core import StringArray

import pvaccess
import numpy as np

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

from malcolm.comms.pva.pvaservercomms import PvaServerComms, PvaGetImplementation, PvaPutImplementation, PvaRpcImplementation, PvaEndpoint, PvaMonitorImplementation


class TestPVAServerComms(unittest.TestCase):

    def setUp(self):
        pvaccess.PvaServer = MagicMock()
        pvaccess.Endpoint = MagicMock()
        pvaccess.PvObject = PvTempObject
        self.p = MagicMock()
        self.p.name = "ProcessName"

    @patch('malcolm.comms.pva.pvaservercomms.PvaRpcImplementation')
    def test_pva_endpoint(self, mock_rpc):
        pva_server_mock = MagicMock()
        server_mock = MagicMock()
        server_mock._get_unique_id = MagicMock(return_value=1)
        pvaccess.Endpoint.registerEndpointGet = MagicMock()
        pvaccess.Endpoint.registerEndpointPut = MagicMock()
        pvaccess.Endpoint.registerEndpointRPC = MagicMock()
        pvaccess.Endpoint.registerEndpointMonitor = MagicMock()
        endpoint = PvaEndpoint("test.name", "test.block", pva_server_mock, server_mock)
        # Test calling of get
        request = MagicMock()
        with patch('malcolm.comms.pva.pvaservercomms.PvaImplementation.wait_for_reply'):
            request.toDict = MagicMock(return_value = {"name1": "val1"})
            endpoint.get_callback(request)
            server_mock._get_unique_id.assert_called_once()
            server_mock.register_get.assert_called_once()
            server_mock.remove_get.assert_called_once()
            server_mock.reset_mock()
            # Test calling of put
            request = MagicMock()
            request.toDict = MagicMock(return_value={"name1": "val1"})
            endpoint.put_callback(request)
            server_mock._get_unique_id.assert_called_once()
            server_mock.register_get.assert_called_once()
            server_mock.remove_get.assert_called_once()
            server_mock.reset_mock()
            # Test calling of monitor
            request = MagicMock()
            request.toDict = MagicMock(return_value={"name1": "val1"})
            endpoint.monitor_callback(request)
            server_mock._get_unique_id.assert_called_once()
            server_mock.register_get.assert_called_once()
            server_mock.remove_get.assert_called_once()
            server_mock.reset_mock()
#        request = MagicMock()
#        endpoint.rpc_callback(request)
#        server_mock._get_unique_id.assert_called_once()
#        server_mock.register_rpc.assert_called_once()
#        server_mock.reset_mock()
#        endpoint.put_callback(request)
#        server_mock._get_unique_id.assert_called_once()
#        server_mock.register_put.assert_called_once()
#        server_mock.get_request.assert_has_calls([call("test.block", request)])
#        server_mock.reset_mock()
#        request = MagicMock()
#        endpoint.monitor_callback(request)
#        server_mock._get_unique_id.assert_called_once()
#        server_mock.register_monitor.assert_called_once()
#        server_mock.get_request.assert_has_calls([call("test.block", request)])

    def test_pva_get_implementation(self):
        server = MagicMock()
        server.get_request = MagicMock(return_value="test_return_1")
        request = MagicMock()
        pva = PvaGetImplementation(1, request, "test.block", server)
        self.assertEqual(pva._id, 1)
        self.assertEqual(pva._block, "test.block")
        self.assertEqual(pva._request, request)
        self.assertEqual(pva._server, server)
        pva._pv_structure = "structure"
        self.assertEqual(pva.getPVStructure(), "structure")
        pva.get()
        #server.get_request.assert_called_with("test.block", request)
        #self.assertEqual(pva.getPVStructure(), "test_return_1")
        #server.get_request = MagicMock(return_value="test_return_2")
        #pva.get()
        #server.get_request.assert_called_with("test.block", request)
        #self.assertEqual(pva.getPVStructure(), "test_return_2")
        #self.assertEqual(pva._name, "test.name")

    def test_pva_put_implementation(self):
        server = MagicMock()
        server.get_request = MagicMock(return_value="test_return_1")
        request = MagicMock()
        pva = PvaPutImplementation(1, request, "test.block", server)
        pva.wait_for_reply = MagicMock()
        self.assertEqual(pva._id, 1)
        self.assertEqual(pva._block, "test.block")
        self.assertEqual(pva._request, request)
        self.assertEqual(pva._server, server)
        pva._pv_structure = "structure"
        self.assertEqual(pva.getPVStructure(), "structure")
        pv = MagicMock()
        pv.toDict =MagicMock(return_value={"item1": {"item2": {}}})
        pva.put(pv)
        server.register_put.assert_called_once()
        pv.toDict.assert_called_once()
        server.send_to_process.assert_called_once()
        pva.wait_for_reply.assert_called_once()

        #server.get_request.assert_called_with("test.block", request)
        #self.assertEqual(pva.getPVStructure(), "test_return_1")
        #path = pva.dict_to_path({'p1': {'p2': {'p3': 'v3'}}})
        #self.assertEqual(path, ['p1', 'p2', 'p3'])
        #value = pva.dict_to_value({'p1': {'p2': {'p3': 'v3'}}})
        #self.assertEqual(value, 'v3')
        #pva._lock = MagicMock()
        #pva._event = MagicMock()
        #pva.check_lock()
        #pva._lock.acquire.assert_has_calls([call(False)])
        #pva.wait_for_reply()
        #pva._event.wait.assert_called_once()
        #response = MagicMock()
        #pva.notify_reply(response)
        #pva._event.set.assert_called_once()
        #self.assertEqual(pva._response, response)
        #server.get_request = MagicMock(return_value="test_return_2")
        #pva.get()
        #server.get_request.assert_called_with("test.block", request)
        #self.assertEqual(pva.getPVStructure(), "test_return_2")
        #pva.dict_to_path = MagicMock()
        #pva.dict_to_value = MagicMock()
        #pv = MagicMock()
        #pva.put(pv)
        #pva.dict_to_path.assert_called_once()
        #pva.dict_to_value.assert_called_once()
        #server.send_to_process.assert_called_once()
        #server.remove_put.assert_called_once()

    def test_pva_rpc_implementation(self):
        server = MagicMock()
        request = {"method": "test_method"}
        pva = PvaRpcImplementation(1, request, "test.block", server)
        self.assertEqual(pva._id, 1)
        self.assertEqual(pva._block, "test.block")
        self.assertEqual(pva._request, request)
        self.assertEqual(pva._server, server)
        self.assertEqual(pva._method, "test_method")
        pre_parse = {"dict1": {"item1", 1}, "list1": [1, 2, 3], "tuple1": ({"item2": 2, "item3": 3}, 2)}
        post_parse = {"dict1": {"item1", 1}, "list1": [1, 2, 3], "tuple1": {"item2": 2, "item3": 3}}
        self.assertEqual(pva.parse_variants(pre_parse), post_parse)
        response = Return(id_=2, value="test.value")
        pva.notify_reply(response)
        pv = MagicMock()
        pva.execute(pv)
        server.process.q.put.assert_called_once()
        pv.toDict.assert_called_once()
        pva._lock = MagicMock()
        pva.check_lock()
        pva._lock.acquire.assert_has_calls([call(False)])
        pva._event = MagicMock()
        pva.wait_for_reply()
        pva._event.wait.assert_called_once()

    def test_pva_monitor_implementation(self):
        request = MagicMock()
        request.toDict = MagicMock(return_value={"item1": {"item2": {}}})
        server = MagicMock()
        structure = MagicMock()
        pva = PvaMonitorImplementation(1, request, "test.block", server)
        self.assertEqual(pva._id, 1)
        self.assertEqual(pva._block, "test.block")
        self.assertEqual(pva._request, request)
        self.assertEqual(pva._server, server)
        self.assertEqual(pva.get_block(), "test.block")
        pva._pv_structure = structure
        self.assertEqual(pva.getPVStructure(), structure)
        pva.mu = MagicMock()
        pva.mu.update = MagicMock()
        self.assertEqual(pva.getUpdater(), pva.mu)
        pva.send_subscription()
        server.send_to_process.assert_called_once()
        pva.update([[["a", "b", "c"], "val1"], [["d", "e", "f"], "val2"]])
        #pva.notify_updates()
        pva.mu.update.assert_not_called()
        pva._pv_structure.hasField = MagicMock(return_value=True)
        pva.update([[["a", "b", "c"], "val3"], [["d", "e", "f"], "val4"]])
        pva.mu.update.assert_called_once()

    def test_init(self):
        self.PVA = PvaServerComms(self.p)

        self.assertEqual("PvaServerComms", self.PVA.name)
        self.assertEqual(self.p, self.PVA.process)

    def test_unique_id(self):
        self.PVA = PvaServerComms(self.p)

        starting_id = self.PVA._current_id
        self.assertEqual(self.PVA._get_unique_id(), starting_id+1)
        self.assertEqual(self.PVA._get_unique_id(), starting_id+2)
        self.assertEqual(self.PVA._get_unique_id(), starting_id+3)
        self.assertEqual(self.PVA._get_unique_id(), starting_id+4)

    def test_update_local_block_list(self):
        self.PVA = PvaServerComms(self.p)
        self.PVA._add_new_pva_channel = MagicMock()

        self.PVA._update_local_block_list({"block1": 1, "block2": 2, "block3": 3})

        calls = [call("block3"), call("block2"), call("block1")]
        self.PVA._add_new_pva_channel.assert_has_calls(calls, any_order=True)

        self.PVA._add_new_pva_channel.reset_mock()
        self.PVA._update_local_block_list({"block1": 1, "block2": 2, "block3": 3, "block4": 4})
        calls = [call("block4")]
        self.PVA._add_new_pva_channel.assert_has_calls(calls, any_order=True)

    def test_update_remote_block_list(self):
        self.PVA = PvaServerComms(self.p)
        self.PVA._add_new_pva_channel = MagicMock()

        self.PVA._update_local_block_list({"block1": 1, "block2": 2, "block3": 3})

        calls = [call("block3"), call("block2"), call("block1")]
        self.PVA._add_new_pva_channel.assert_has_calls(calls, any_order=True)

        self.PVA._add_new_pva_channel.reset_mock()
        self.PVA._update_local_block_list({"block1": 1, "block2": 2, "block3": 3, "block4": 4})
        calls = [call("block4")]
        self.PVA._add_new_pva_channel.assert_has_calls(calls, any_order=True)

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
        response3 = Return(id_=3)
        self.PVA.send_to_client(response3)
        rpc_mock1.notify_reply.assert_has_calls([call(response1)])
        rpc_mock2.notify_reply.assert_has_calls([call(response2)])
        # Gets
        get_mock1 = MagicMock()
        get_mock2 = MagicMock()
        self.PVA._gets[3] = get_mock1
        self.PVA._gets[4] = get_mock2
        response1 = Return(id_=3)
        self.PVA.send_to_client(response1)
        get_mock1.notify_reply.assert_has_calls([call(response1)])
        response2 = Error(id_=4)
        self.PVA.send_to_client(response2)
        get_mock2.notify_reply.assert_has_calls([call(response2)])
        response3 = Return(id_=5)
        self.PVA.send_to_client(response3)
        get_mock1.notify_reply.assert_has_calls([call(response1)])
        get_mock2.notify_reply.assert_has_calls([call(response2)])
        # Puts
        put_mock1 = MagicMock()
        put_mock2 = MagicMock()
        self.PVA._puts[5] = put_mock1
        self.PVA._puts[6] = put_mock2
        response1 = Return(id_=5)
        self.PVA.send_to_client(response1)
        put_mock1.notify_reply.assert_has_calls([call(response1)])
        response2 = Error(id_=6)
        self.PVA.send_to_client(response2)
        put_mock2.notify_reply.assert_has_calls([call(response2)])
        response3 = Return(id_=7)
        self.PVA.send_to_client(response3)
        put_mock1.notify_reply.assert_has_calls([call(response1)])
        put_mock2.notify_reply.assert_has_calls([call(response2)])
        # Monitors
        mon_mock1 = MagicMock()
        mon_mock2 = MagicMock()
        self.PVA._monitors[7] = mon_mock1
        self.PVA._monitors[8] = mon_mock2
        response1 = Return(id_=7)
        self.PVA.send_to_client(response1)
        mon_mock1.notify_reply.assert_has_calls([call(response1)])
        response2 = Error(id_=8)
        self.PVA.send_to_client(response2)
        mon_mock2.notify_reply.assert_has_calls([call(response2)])
        response3 = Return(id_=9)
        self.PVA.send_to_client(response3)
        mon_mock1.notify_reply.assert_has_calls([call(response1)])
        mon_mock2.notify_reply.assert_has_calls([call(response2)])
        # Delta
        mon_mock3 = MagicMock()
        self.PVA._monitors[9] = mon_mock3
        response3 = Delta(id_=9)
        self.PVA.send_to_client(response3)
        mon_mock3.update.assert_has_calls([call(response3["changes"])])
        # Updates
        self.PVA._update_local_block_list = MagicMock()
        self.PVA._update_remote_block_list = MagicMock()
        response4 = Update(id_=self.PVA._local_block_id)
        response5 = Update(id_=self.PVA._remote_block_id)
        self.PVA.send_to_client(response4)
        self.PVA._update_local_block_list.assert_called_once()
        self.PVA.send_to_client(response5)
        self.PVA._update_remote_block_list.assert_called_once()

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

    def test_register_monitor(self):
        self.PVA = PvaServerComms(self.p)
        self.mon = MagicMock()
        self.PVA.register_monitor(1, self.mon)
        self.assertEqual(self.PVA._monitors, {1: self.mon})

    def test_register_get(self):
        self.PVA = PvaServerComms(self.p)
        self.get = MagicMock()
        self.PVA.register_get(1, self.get)
        self.assertEqual(self.PVA._gets, {1: self.get})

    def test_remove_get(self):
        self.PVA = PvaServerComms(self.p)
        get1 = MagicMock()
        get2 = MagicMock()
        self.PVA._gets = {1: get1, 2: get2}
        self.PVA.remove_get(1)
        self.assertEqual(self.PVA._gets, {2: get2})

    def test_register_put(self):
        self.PVA = PvaServerComms(self.p)
        self.put = MagicMock()
        self.PVA.register_put(1, self.put)
        self.assertEqual(self.PVA._puts, {1: self.put})

    def test_remove_put(self):
        self.PVA = PvaServerComms(self.p)
        put1 = MagicMock()
        put2 = MagicMock()
        self.PVA._puts = {1: put1, 2: put2}
        self.PVA.remove_put(1)
        self.assertEqual(self.PVA._puts, {2: put2})

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

    def test_dict_to_stucture(self):
        self.PVA = PvaServerComms(self.p)
        val_dict = OrderedDict()
        val_dict["typeid"] = "type1"
        val_dict["val1"] = "1"
        val_dict["val2"] = np.int32(2)
        val_dict["val3"] = True
        val_dict["val4"] = np.int64(0)
        val_dict["val5"] = np.float64(0.5)
        val_dict["val6"] = StringArray('', '')
        val_dict["val7"] = np.array([5, 1], dtype=np.int32)
        val_dict["val8"] = [True, False]
        val_dict["val9"] = np.array([0, 1], dtype=np.int64)
        val_dict["val10"] = np.array([0.2, 0.6], dtype=np.float64)
        val = self.PVA.pva_structure_from_value(val_dict)
        test_dict = OrderedDict()
        test_dict["val1"] = pvaccess.STRING
        test_dict["val2"] = pvaccess.INT
        test_dict["val3"] = pvaccess.BOOLEAN
        test_dict["val4"] = pvaccess.LONG
        test_dict["val5"] = pvaccess.DOUBLE
        test_dict["val6"] = [pvaccess.STRING]
        test_dict["val7"] = [pvaccess.INT]
        test_dict["val8"] = [pvaccess.BOOLEAN]
        test_dict["val9"] = [pvaccess.LONG]
        test_dict["val10"] = [pvaccess.DOUBLE]
        test_val = pvaccess.PvObject(test_dict, "type1")
        self.assertEquals(val, test_val)

        # Test the variant union array type
        val = self.PVA.pva_structure_from_value(
            {"union_array": [
                {"val1": 1},
                {"val2": "2"}
            ]})
        test_dict = OrderedDict()
        test_dict["union_array"] = [()]
        test_val = pvaccess.PvObject(test_dict, "")
        self.assertEquals(val, test_val)
        val = self.PVA.pva_structure_from_value(
            {"union_array": []})
        test_dict = OrderedDict()
        test_dict["union_array"] = [()]
        test_val = pvaccess.PvObject(test_dict, "")
        self.assertEquals(val, test_val)

    def test_dict_to_pv(self):
        self.PVA = PvaServerComms(self.p)
        val_dict = OrderedDict()
        val_dict["typeid"] = "type1"
        val_dict["val1"] = StringArray('', '')
        val_dict["val2"] = np.array((1, 2))
        val_dict["val3"] = dict(a=43)
        val_dict["val4"] = [True, False]
        val_dict["val5"] = [dict(a=43), dict(b=44)]
        val_dict["val6"] = "s"
        actual = self.PVA.dict_to_pv_object(val_dict)
        self.assertEqual(actual._type, "type1")
        self.assertEqual(actual._dict["val1"], ["", ""])
        self.assertEqual(actual._dict["val2"], [1, 2])
        self.assertEqual(actual._dict["val3"], dict(a=43))
        self.assertEqual(actual._dict["val4"], [True, False])
        self.assertEqual(len(actual._dict["val5"]), 2)
        self.assertEqual(actual._dict["val5"][0]._dict, dict(a=43))
        self.assertEqual(actual._dict["val5"][1]._dict, dict(b=44))
        self.assertEqual(actual._dict["val6"], "s")




if __name__ == "__main__":
    unittest.main(verbosity=2)
