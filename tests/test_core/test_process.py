import os
import sys
import time
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict
# import logging
# logging.basicConfig(level=logging.DEBUG)

import unittest
from mock import MagicMock, ANY

# module imports
from malcolm.core.process import \
    Process, BlockChanges, PROCESS_STOP, BlockAdd, BlockRespond, \
    BlockList
from malcolm.core.syncfactory import SyncFactory
from malcolm.core.request import Subscribe, Unsubscribe, Post, Get
from malcolm.core.response import Return, Update, Delta, Error
from malcolm.core.ntscalararray import NTScalarArray
from malcolm.core.vmetas import StringArrayMeta
from malcolm.core.block import Block


class TestProcess(unittest.TestCase):

    def test_init(self):
        s = MagicMock()
        p = Process("proc", s)
        s.create_queue.assert_called_once_with()
        self.assertEqual(p.q, s.create_queue.return_value)

    def test_add_block(self):
        p = Process("proc", MagicMock())
        b = Block()
        b.set_process_path(p, ("name",))
        c = MagicMock()
        p.add_block(b, c)
        self.assertEqual(p._blocks["name"], b)
        self.assertEqual(p._controllers["name"], c)

    def test_get_block(self):
        p = Process("proc", MagicMock())
        p.process_block["remoteBlocks"].set_value(['name1'])
        b1 = p.get_block("name1")
        self.assertEqual(b1.status, "Waiting for connection...")
        self.assertEqual(p.get_block("name1"), b1)
        b2 = Block()
        b2.set_process_path(p, ("name2",))
        c = MagicMock()
        p.add_block(b2, c)
        self.assertEqual(p.get_block("name2"), b2)
        self.assertEqual(p.get_controller("name2"), c)

    def test_add_block_calls_handle(self):
        s = SyncFactory("sched")
        p = Process("proc", s)
        b = Block()
        c = MagicMock()
        b.set_process_path(p, ("myblock",))
        p.add_block(b, c)
        p.start()
        p.stop()
        self.assertEqual(len(p._blocks), 2)
        self.assertEqual(p._blocks, dict(myblock=b, proc=p.process_block))

    def test_starting_process(self):
        s = SyncFactory("sched")
        p = Process("proc", s)
        b = MagicMock()
        p._handle_block_add(BlockAdd(b, "myblock", None))
        self.assertEqual(p._blocks, dict(myblock=b, proc=ANY))
        p.start()
        request = Post(MagicMock(), MagicMock(), ["myblock", "foo"])
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
        s = SyncFactory("sched")
        p = Process("proc", s)

        def sleep(n, a=None):
            time.sleep(a)
        f = MagicMock(side_effect=sleep)

        spawned = p.spawn(f, "fred", a=0.05)
        p.start()
        p.stop()
        self.assertEqual(p._other_spawned, [(spawned, f)])
        f.assert_called_once_with("fred", a=0.05)

    def test_get(self):
        p = Process("proc", MagicMock())
        block = MagicMock()
        block.to_dict = MagicMock(
            return_value={"path_1": {"path_2": {"attr": "value"}}})
        request = Get(MagicMock(), MagicMock(), ["myblock", "path_1", "path_2"])
        request.response_queue.qsize.return_value = 0
        p._handle_block_add(BlockAdd(block, "myblock", None))
        p.q.get = MagicMock(side_effect=[request, PROCESS_STOP])

        p.recv_loop()

        response = request.response_queue.put.call_args[0][0]
        self.assertIsInstance(response, Return)
        self.assertEquals({"attr": "value"}, response.value)

    def test_block_respond(self):
        p = Process("proc", MagicMock())
        p.q.put = MagicMock()
        response = MagicMock()
        response_queue = MagicMock()
        p.block_respond(response, response_queue)
        block_response = p.q.put.call_args[0][0]
        self.assertEquals(block_response.response, response)
        self.assertEquals(block_response.response_queue, response_queue)

    def test_block_respond_triggers_response(self):
        p = Process("proc", MagicMock())
        response = MagicMock()
        response_queue = MagicMock()
        p.q.get = MagicMock(
            side_effect=[BlockRespond(response, response_queue), PROCESS_STOP])

        p.recv_loop()

        response_queue.put.assert_called_once_with(response)

    def test_make_process_block(self):
        p = Process("proc", MagicMock())
        p_block = p.process_block
        self.assertEquals(p_block.process_path, ["proc"])
        self.assertEquals(NTScalarArray, type(p_block["blocks"]))
        self.assertEquals(StringArrayMeta, type(p_block["blocks"].meta))
        self.assertEquals(("proc",), p_block.blocks)
        self.assertEquals("Blocks hosted by this Process",
                          p_block["blocks"].meta.description)

    def test_update_block_list(self):
        p = Process("proc", MagicMock())
        p.q.reset_mock()
        p.update_block_list("cc", ["myblock"])
        request = BlockList(client_comms="cc", blocks=["myblock"])
        p.q.put.assert_called_once_with(request)
        self.assertEqual(p._client_comms, {})
        p._handle_block_list(request)
        self.assertEqual(p._client_comms, dict(cc=["myblock"]))
        self.assertEqual(p.process_block.remoteBlocks, ("myblock",))
        self.assertEqual(p.get_client_comms("myblock"), "cc")


class TestSubscriptions(unittest.TestCase):

    def test_report_changes(self):
        change = [["path"], "value"]
        s = MagicMock()
        p = Process("proc", s)
        s.reset_mock()
        p.report_changes(change)
        p.q.put.assert_called_once_with(BlockChanges(changes=[change]))

    def test_subscribe(self):
        block = MagicMock(
            to_dict=MagicMock(
                return_value={"attr": "value", "inner": {"attr2": "other"}}))
        p = Process("proc", MagicMock())
        sub_1 = Subscribe(
            MagicMock(), MagicMock(), ["block"], False)
        sub_1.response_queue.qsize.return_value = 0
        sub_2 = Subscribe(
            MagicMock(), MagicMock(), ["block", "inner"], True)
        sub_2.response_queue.qsize.return_value = 0
        p.q.get = MagicMock(side_effect=[sub_1, sub_2, PROCESS_STOP])

        p._handle_block_add(BlockAdd(block, "block", None))
        p.recv_loop()

        self.assertEquals([sub_1, sub_2], list(p._subscriptions.values()))
        response_1 = sub_1.response_queue.put.call_args[0][0]
        response_2 = sub_2.response_queue.put.call_args[0][0]
        self.assertEquals({"attr": "value", "inner": {"attr2": "other"}},
                          response_1.value)
        self.assertEquals([[[], {"attr2": "other"}]], response_2.changes)

    def test_partial_structure_subscriptions(self):
        block_1 = MagicMock(
            to_dict=MagicMock(
                return_value={"attr": "value", "inner": {"attr2": "value"}}))
        block_2 = MagicMock(
            to_dict=MagicMock(return_value={"attr": "value"}))

        sub_1 = Subscribe(None, MagicMock(), ["block_1", "inner"], delta=False)
        sub_1.set_id(1)
        sub_1.response_queue.qsize.return_value = 0

        sub_2 = Subscribe(None, MagicMock(), ["block_1"], delta=True)
        sub_2.set_id(2)
        sub_2.response_queue.qsize.return_value = 0

        sub_3 = Subscribe(None, MagicMock(), ["block_1", "inner", "attr2"],
                          delta=False)
        sub_3.set_id(3)
        sub_3.response_queue.qsize.return_value = 0

        changes_1 = [[["block_1", "inner", "attr2"], "new_value"],
                     [["block_1", "attr"], "new_value"]]
        changes_2 = [[["block_2", "attr"], "block_2_value"]]
        request_1 = BlockChanges(changes_1)
        request_2 = BlockChanges(changes_2)
        p = Process("proc", MagicMock())
        p.q.get = MagicMock(side_effect=[
            sub_1, sub_2, sub_3, request_1, request_2,
            PROCESS_STOP])

        p._handle_block_add(BlockAdd(block_1, "block_1", None))
        p._handle_block_add(BlockAdd(block_2, "block_2", None))
        p.recv_loop()

        response_1 = sub_1.response_queue.put.call_args_list[1][0][0]["value"]
        self.assertEquals({"attr2": "new_value"}, response_1)

        response_2 = sub_2.response_queue.put.call_args_list[1][0][0]["changes"]
        self.assertEquals([[["inner", "attr2"], "new_value"],
                           [["attr"], "new_value"]], response_2)

        response_3 = sub_3.response_queue.put.call_args_list[1][0][0]["value"]
        self.assertEquals("new_value", response_3)

    def test_unsubscribe(self):
        # Test that we remove the relevant subscription only and that
        # updates are no longer sent
        block = MagicMock(
            to_dict=MagicMock(
                return_value={"attr": "0", "inner": {"attr2": "other"}}))
        p = Process("proc", MagicMock())
        sub_1 = Subscribe(
            MagicMock(), MagicMock(), ["block"], False)
        sub_1.response_queue.qsize.return_value = 0
        sub_2 = Subscribe(
            MagicMock(), MagicMock(), ["block"], False)
        sub_2.response_queue.qsize.return_value = 0
        sub_1.set_id(1234)
        sub_2.set_id(1234)
        change_1 = BlockChanges([[["block", "attr"], "1"]])
        change_2 = BlockChanges([[["block", "attr"], "2"]])
        unsub_1 = Unsubscribe(sub_1.context, sub_1.response_queue)
        unsub_1.set_id(sub_1.id)

        p.q.get = MagicMock(side_effect=[sub_1, sub_2, change_1,
                                         unsub_1, change_2, PROCESS_STOP])
        p._handle_block_add(BlockAdd(block, "block", None))
        p.recv_loop()

        self.assertEqual([sub_2], list(p._subscriptions.values()))

        sub_1_responses = sub_1.response_queue.put.call_args_list
        sub_2_responses = sub_2.response_queue.put.call_args_list
        self.assertEquals(3, len(sub_1_responses))
        self.assertEquals(sub_1_responses[0][0][0].value["attr"], "0")
        self.assertEquals(sub_1_responses[1][0][0].value["attr"], "1")
        self.assertIsInstance(sub_1_responses[2][0][0], Return)
        self.assertEquals(3, len(sub_2_responses))
        self.assertEquals(sub_2_responses[0][0][0].value["attr"], "0")
        self.assertEquals(sub_2_responses[1][0][0].value["attr"], "1")
        self.assertEquals(sub_2_responses[2][0][0].value["attr"], "2")

    def test_unsubscribe_error(self):
        p = Process("proc", MagicMock())
        unsub = Unsubscribe(MagicMock(), MagicMock())
        unsub.set_id(1234)
        unsub.response_queue.qsize.return_value = 0
        p.q.get = MagicMock(side_effect=[unsub, PROCESS_STOP])

        p.recv_loop()

        responses = unsub.response_queue.put.call_args_list
        self.assertEquals(1, len(responses))
        response = responses[0][0][0]
        self.assertEquals(Error, type(response))

if __name__ == "__main__":
    unittest.main(verbosity=2)
