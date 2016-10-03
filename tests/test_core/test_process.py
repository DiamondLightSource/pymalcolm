import os
import sys
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
        b.set_parent(p, "name")
        p.add_block(b)
        self.assertEqual(p._blocks["name"], b)

    def test_add_block_calls_handle(self):
        s = SyncFactory("sched")
        p = Process("proc", s)
        b = Block()
        b.set_parent(p, "myblock")
        p.add_block(b)
        p.start()
        p.stop()
        self.assertEqual(len(p._blocks), 2)
        self.assertEqual(p._blocks, dict(myblock=b, proc=p.process_block))

    def test_starting_process(self):
        s = SyncFactory("sched")
        p = Process("proc", s)
        b = MagicMock()
        p._handle_block_add(BlockAdd(b, "myblock"))
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
        s = MagicMock()
        p = Process("proc", s)
        spawned = p.spawn(callable, "fred", a=4)
        self.assertEqual(spawned, s.spawn.return_value)
        self.assertEqual(p._other_spawned, [spawned])
        s.spawn.assert_called_once_with(callable, "fred", a=4)

    def test_get(self):
        p = Process("proc", MagicMock())
        block = MagicMock()
        block.to_dict = MagicMock(
            return_value={"path_1": {"path_2": {"attr": "value"}}})
        request = Get(MagicMock(), MagicMock(), ["myblock", "path_1", "path_2"])
        p._handle_block_add(BlockAdd(block, "myblock"))
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
        self.assertEquals(p_block.path_relative_to(p), ["proc"])
        self.assertEquals(NTScalarArray, type(p_block["blocks"]))
        self.assertEquals(StringArrayMeta, type(p_block["blocks"].meta))
        self.assertEquals(["proc"], p_block.blocks)
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
        self.assertEqual(p.process_block.remoteBlocks, ["myblock"])
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
        sub_2 = Subscribe(
            MagicMock(), MagicMock(), ["block", "inner"], True)
        p.q.get = MagicMock(side_effect=[sub_1, sub_2, PROCESS_STOP])

        p._handle_block_add(BlockAdd(block, "block"))
        p.recv_loop()

        self.assertEquals([sub_1, sub_2], p._subscriptions)
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

        sub_1 = MagicMock()
        sub_1.endpoint = ["block_1", "inner"]
        sub_1.delta = False
        sub_2 = MagicMock()
        sub_2.endpoint = ["block_1", "inner"]
        sub_2.delta = True

        changes_1 = [[["block_1", "inner", "attr2"], "new_value"],
                     [["block_1", "attr"], "new_value"]]
        changes_2 = [[["block_2", "attr"], "block_2_value"]]
        request_1 = BlockChanges(changes_1)
        request_2 = BlockChanges(changes_2)
        p = Process("proc", MagicMock())
        p.q.get = MagicMock(side_effect=[
            request_1, request_2,
            PROCESS_STOP])
        p._subscriptions = [sub_1, sub_2]

        p._handle_block_add(BlockAdd(block_1, "block_1"))
        p._handle_block_add(BlockAdd(block_2, "block_2"))
        p.recv_loop()

        response_1 = sub_1.respond_with_update.call_args[0][0]
        response_2 = sub_2.respond_with_delta.call_args[0][0]
        self.assertEquals({"attr2": "new_value"}, response_1)
        self.assertEquals([[["attr2"], "new_value"]], response_2)

    def test_unsubscribe(self):
        # Test that we remove the relevant subscription only and that
        # updates are no longer sent
        block = MagicMock(
            to_dict=MagicMock(
                return_value={"attr": "0", "inner": {"attr2": "other"}}))
        p = Process("proc", MagicMock())
        sub_1 = Subscribe(
            MagicMock(), MagicMock(), ["block"], False)
        sub_2 = Subscribe(
            MagicMock(), MagicMock(), ["block"], False)
        sub_1.set_id(1234)
        sub_2.set_id(4321)
        change_1 = BlockChanges([[["block", "attr"], "1"]])
        change_2 = BlockChanges([[["block", "attr"], "2"]])
        unsub_1 = Unsubscribe(MagicMock(), MagicMock())
        unsub_1.set_id(1234)

        p.q.get = MagicMock(side_effect=[sub_1, sub_2, change_1,
                                         unsub_1, change_2, PROCESS_STOP])
        p._handle_block_add(BlockAdd(block, "block"))
        p.recv_loop()

        self.assertEqual([sub_2], p._subscriptions)
        self.assertEquals(1, len(unsub_1.response_queue.put.call_args_list))
        response = unsub_1.response_queue.put.call_args_list[0][0][0]
        self.assertIsNone(response.value)
        self.assertIs(unsub_1.context, response.context)

        sub_1_responses = sub_1.response_queue.put.call_args_list
        sub_2_responses = sub_2.response_queue.put.call_args_list
        self.assertEquals(2, len(sub_1_responses))
        self.assertEquals(3, len(sub_2_responses))

    def test_unsubscribe_error(self):
        p = Process("proc", MagicMock())
        unsub = Unsubscribe(MagicMock(), MagicMock())
        unsub.set_id(1234)
        p.q.get = MagicMock(side_effect=[unsub, PROCESS_STOP])

        p.recv_loop()

        responses = unsub.response_queue.put.call_args_list
        self.assertEquals(1, len(responses))
        response = responses[0][0][0]
        self.assertEquals(Error, type(response))
        self.assertEquals(
            "No subscription found for id 1234", response.message)

if __name__ == "__main__":
    unittest.main(verbosity=2)
