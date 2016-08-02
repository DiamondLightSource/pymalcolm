import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock, patch, call

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.controllers import ClientController, HelloController
from malcolm.core.block import Block
from malcolm.metas import StringMeta
from malcolm.compat import queue

class TestClientController(unittest.TestCase):

    def setUp(self):
        # Serialized version of the block we want
        source = Block()
        HelloController(MagicMock(), source, "blockname")
        self.serialized = source.to_dict()
        # Setup client controller prerequisites
        self.b = Block()
        self.b.name = "blockname"
        self.p = MagicMock()
        self.comms = MagicMock()
        self.cc = ClientController(self.p, self.b, "blockname")
        # get process to give us comms
        self.p.get_client_comms.return_value = self.comms
        # tell our controller which blocks the process can talk to
        response = MagicMock(id_=self.cc.REMOTE_BLOCKS_ID, value=["blockname"])
        self.cc.put(response)
        # tell our controller the serialized state of the block
        response = MagicMock(id_=self.cc.BLOCK_ID, changes=[[[], self.serialized]])
        self.cc.put(response)

    def test_init(self):
        self.assertEqual(self.p.q.put.call_count, 1)
        req = self.p.q.put.call_args[0][0]
        self.assertEqual(req.typeid, "malcolm:core/Subscribe:1.0")
        self.assertEqual(req.endpoint, [self.p.name, "remoteBlocks", "value"])
        self.assertEqual(req.response_queue, self.cc)
        self.p.get_client_comms.assert_called_with("blockname")
        self.assertEqual(self.comms.q.put.call_count, 1)
        req = self.comms.q.put.call_args[0][0]
        self.assertEqual(req.typeid, "malcolm:core/Subscribe:1.0")
        self.assertEqual(req.delta, True)
        self.assertEqual(req.response_queue, self.cc)
        self.assertEqual(req.endpoint, ["blockname"])

    def test_methods_created(self):
        self.assertEqual(list(self.b.methods), ["reset", "say_hello", "disable"])
        m = self.b.methods["say_hello"]
        self.assertEqual(m.name, "say_hello")
        self.assertEqual(list(m.takes.elements), ["name"])
        self.assertEqual(type(m.takes.elements["name"]), StringMeta)
        self.assertEqual(list(m.returns.elements), ["greeting"])
        self.assertEqual(type(m.returns.elements["greeting"]), StringMeta)
        self.assertEqual(m.defaults, {})

    def test_call_method(self):
        self.p.create_queue.return_value = queue.Queue()
        def f(request):
            request.respond_with_return(dict(
                greeting="Hello %s" % request.parameters.name))
        self.comms.q.put.side_effect = f
        ret = self.b.say_hello(name="me")
        self.assertEqual(ret.greeting, "Hello me")

    def test_put_update_response(self):
        response = MagicMock(
            id_=self.cc.BLOCK_ID,
            changes=[[["substructure"], "change"]])
        self.b.update = MagicMock()
        self.cc.put(response)
        self.b.update.assert_called_once_with([["substructure"], "change"])

    def test_put_root_update_response(self):
        attr1 = StringMeta("dummy")
        attr2 = StringMeta("dummy2")
        new_block_structure = {}
        new_block_structure["attr1"] = attr1.to_dict()
        new_block_structure["attr2"] = attr2.to_dict()
        self.b.replace_children = MagicMock()
        response = MagicMock(
            id_=self.cc.BLOCK_ID,
            changes=[[[], new_block_structure]])
        self.cc.put(response)
        self.assertIs(self.b, self.cc.block)
        deserialized_changes = self.b.replace_children.call_args_list[0][0][0]
        serialized_changes = [x.to_dict() for x in
                              deserialized_changes.values()]
        expected = [attr1.to_dict(), attr2.to_dict()]
        # dicts are not hashable, so cannot use set compare
        for x in expected:
            self.assertTrue(x in serialized_changes)
        for x in serialized_changes:
            self.assertTrue(x in expected)



if __name__ == "__main__":
    unittest.main(verbosity=2)
