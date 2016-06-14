import unittest
import sys
import os
from collections import OrderedDict
# import logging
# logging.basicConfig(level=logging.DEBUG)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# mock
from pkg_resources import require
require("mock")
from mock import MagicMock

# module imports
from malcolm.core.process import \
        Process, BlockChanged, BlockNotify, PROCESS_STOP
from malcolm.core.syncfactory import SyncFactory
from malcolm.core.request import Request
from malcolm.core.response import Response


class TestProcess(unittest.TestCase):

    def test_init(self):
        s = MagicMock()
        p = Process("proc", s)
        s.create_queue.assert_called_once_with()
        self.assertEqual(p.q, s.create_queue.return_value)

    def test_add_block(self):
        p = Process("proc", MagicMock())
        b = MagicMock()
        b.name = "myblock"
        p.add_block(b)
        self.assertIs(p, b.parent)

    def test_starting_process(self):
        s = SyncFactory("sched")
        p = Process("proc", s)
        b = MagicMock()
        b.name = "myblock"
        p.add_block(b)
        self.assertEqual(p._blocks, dict(myblock=b))
        p.start()
        request = MagicMock()
        request.type_ = Request.POST
        request.endpoint = ["myblock", "foo"]
        p.q.put(request)
        # wait for spawns to have done their job
        p.stop()
        b.handle_request.assert_called_once_with(request)

    def test_error(self):
        s = SyncFactory("sched")
        p = Process("proc", s)
        p.log_exception = MagicMock()
        p.start()
        request = MagicMock()
        request.endpoint = ["anything"]
        p.q.put(request)
        p.stop()
        p.log_exception.assert_called_once_with("Exception while handling %s",
                                                request)

    def test_spawned_adds_to_other_spawned(self):
        s = MagicMock()
        p = Process("proc", s)
        spawned = p.spawn(callable, "fred", a=4)
        self.assertEqual(spawned, s.spawn.return_value)
        self.assertEqual(p._other_spawned, [spawned])
        s.spawn.assert_called_once_with(callable, "fred", a=4)

    def test_get(self):
        p = Process("proc", MagicMock())
        block = MagicMock()
        block.name = "myblock"
        block.to_dict = MagicMock(
            return_value={"path_1":{"path_2":{"attr":"value"}}})
        request = MagicMock()
        request.type_ = Request.GET
        request.endpoint = ["myblock", "path_1", "path_2"]
        p.add_block(block)
        p.q.get = MagicMock(side_effect=[request, PROCESS_STOP])

        p.recv_loop()

        response = request.response_queue.put.call_args[0][0]
        self.assertEquals(Response.RETURN, response.type_)
        self.assertEquals({"attr":"value"}, response.value)

class TestSubscriptions(unittest.TestCase):

    def test_on_changed(self):
        changes = [[["path"], "value"]]
        s = MagicMock()
        p = Process("proc", s)
        p.on_changed(changes)
        p.q.put.assert_called_once_with(BlockChanged(changes=changes))

    def test_notify(self):
        s = MagicMock()
        p = Process("proc", s)
        p.notify_subscribers("block")
        p.q.put.assert_called_once_with(BlockNotify(name="block"))

    def test_subscribe(self):
        block = MagicMock(
            to_dict=MagicMock(
                return_value={"attr":"value", "inner":{"attr2":"other"}}))
        block.name = "block"
        p = Process("proc", MagicMock())
        sub_1 = Request.Subscribe(
            MagicMock(), MagicMock(), ["block"], False)
        sub_2 = Request.Subscribe(
            MagicMock(), MagicMock(), ["block", "inner"], True)
        p.q.get = MagicMock(side_effect = [sub_1, sub_2, PROCESS_STOP])

        p.add_block(block)
        p.recv_loop()

        self.assertEquals(OrderedDict(block=[sub_1, sub_2]),
                          p._subscriptions)
        response_1 = sub_1.response_queue.put.call_args[0][0]
        response_2 = sub_2.response_queue.put.call_args[0][0]
        self.assertEquals({"attr":"value", "inner":{"attr2":"other"}},
                          response_1.value)
        self.assertEquals({"attr2":"other"}, response_2.value)

    def test_overlapped_changes(self):
        block = MagicMock(
            to_dict=MagicMock(return_value={"attr":"value", "attr2":"other"}))
        block.name = "block"
        sub_1 = MagicMock()
        sub_1.endpoint = ["block"]
        sub_1.delta = False
        sub_2 = MagicMock()
        sub_2.endpoint = ["block"]
        sub_2.delta = True
        changes_1 = [[["block", "attr"], "changing_value"]]
        changes_2 = [[["block", "attr"], "final_value"]]
        request_1 = BlockChanged(changes_1)
        request_2 = BlockChanged(changes_2)
        request_3 = BlockNotify(block.name)
        s = MagicMock()
        p = Process("proc", s)
        p._subscriptions["block"] = [sub_1, sub_2]
        p.q.get = MagicMock(
            side_effect = [request_1, request_2, request_3, PROCESS_STOP])

        p.add_block(block)
        p.recv_loop()

        sub_1.response_queue.put.assert_called_once()
        sub_2.response_queue.put.assert_called_once()
        response_1 = sub_1.response_queue.put.call_args[0][0]
        response_2 = sub_2.response_queue.put.call_args[0][0]
        self.assertEquals({"attr":"final_value", "attr2":"other"},
                          response_1.value)
        self.assertEquals(
            [[["attr"], "changing_value"], [["attr"], "final_value"]],
            response_2.changes)

    def test_partial_structure_subscriptions(self):
        block_1 = MagicMock(
            to_dict=MagicMock(
                return_value={"attr":"value", "inner":{"attr2":"value"}}))
        block_1.name = "block_1"
        block_2 = MagicMock(
            to_dict=MagicMock(return_value={"attr":"value"}))
        block_2.name = "block_2"

        sub_1 = MagicMock()
        sub_1.endpoint = ["block_1", "inner"]
        sub_1.delta = False
        sub_2 = MagicMock()
        sub_2.endpoint = ["block_1", "inner"]
        sub_2.delta = True

        changes_1 = [[["block_1", "inner", "attr2"], "new_value"],
            [["block_1", "attr"], "new_value"]]
        changes_2 = [[["block_2", "attr"], "block_2_value"]]
        request_1 = BlockChanged(changes_1)
        request_2 = BlockChanged(changes_2)
        request_3 = BlockNotify(block_1.name)
        request_4 = BlockNotify(block_2.name)
        p = Process("proc", MagicMock())
        p.q.get = MagicMock(side_effect = [request_1, request_2, request_3,
                                           request_4, PROCESS_STOP])
        p._subscriptions["block_1"] = [sub_1, sub_2]

        p.add_block(block_1)
        p.add_block(block_2)
        p.recv_loop()

        response_1 = sub_1.response_queue.put.call_args[0][0]
        response_2 = sub_2.response_queue.put.call_args[0][0]
        self.assertEquals({"attr2":"new_value"}, response_1.value)
        self.assertEquals([[["attr2"], "new_value"]], response_2.changes)

    def test_multiple_notifies_single_change(self):
        block_1 = MagicMock(
            to_dict=MagicMock(return_value={"attr":"initial_value"}))
        block_1.name = "block_1"
        block_2 = MagicMock(
            to_dict=MagicMock(return_value={"attr2":"initial_value"}))
        block_2.name = "block_2"
        sub_1 = MagicMock()
        sub_1.endpoint = ["block_1"]
        sub_1.delta = False
        sub_2 = MagicMock()
        sub_2.endpoint = ["block_1"]
        sub_2.delta = True
        sub_3 = MagicMock()
        sub_3.endpoint = ["block_2"]
        sub_3.delta = False
        sub_4 = MagicMock()
        sub_4.endpoint = ["block_2"]
        sub_4.delta = True
        change_1 = [[["block_1", "attr"], "final_value"]]
        change_2 = [[["block_2", "attr2"], "final_value"]]
        request_1 = BlockNotify("block_1")
        request_2 = BlockChanged(change_1)
        request_3 = BlockChanged(change_2)
        request_4 = BlockNotify("block_1")
        request_5 = BlockNotify("block_1")
        request_6 = BlockNotify("block_2")
        p = Process("proc", MagicMock())
        p.q.get = MagicMock(side_effect = [request_1, request_2, request_3,
                                           request_4, request_5, request_6,
                                           PROCESS_STOP])
        p.q.put = MagicMock(side_effect = p.q.put)
        p._subscriptions["block_1"] = [sub_1, sub_2]
        p._subscriptions["block_2"] = [sub_3, sub_4]
        p.add_block(block_1)
        p.add_block(block_2)

        p.recv_loop()

        call_list = sub_1.response_queue.put.call_args_list
        self.assertEquals(1, len(call_list))
        self.assertEquals(Response.UPDATE, call_list[0][0][0].type_)
        self.assertEquals({"attr":"final_value"}, call_list[0][0][0].value)

        call_list = sub_2.response_queue.put.call_args_list
        self.assertEquals(1, len(call_list))
        self.assertEquals(Response.DELTA, call_list[0][0][0].type_)
        self.assertEquals([[["attr"], "final_value"]],
                          call_list[0][0][0].changes)

        call_list = sub_3.response_queue.put.call_args_list
        self.assertEquals(1, len(call_list))
        self.assertEquals(Response.UPDATE, call_list[0][0][0].type_)
        self.assertEquals({"attr2":"final_value"}, call_list[0][0][0].value)

        call_list = sub_4.response_queue.put.call_args_list
        self.assertEquals(1, len(call_list))
        self.assertEquals(Response.DELTA, call_list[0][0][0].type_)
        self.assertEquals([[["attr2"], "final_value"]],
                          call_list[0][0][0].changes)

if __name__ == "__main__":
    unittest.main(verbosity=2)
