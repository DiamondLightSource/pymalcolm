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
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core import Attribute, ClientController
from malcolm.core.vmetas import StringMeta, NumberMeta
from malcolm.compat import queue
from malcolm.parts.demo import HelloPart


class TestClientController(unittest.TestCase):

    def setUp(self):
        p = MagicMock()
        part = HelloPart(p, None)
        # Serialized version of the block we want
        source = DefaultController(
            "blockname", p, parts={"hello":part}).block
        self.serialized = source.to_dict()
        # Setup client controller prerequisites
        self.p = MagicMock()
        self.p.name = "process"
        self.comms = MagicMock()
        self.cc = ClientController("blockname", self.p)
        self.b = self.cc.block
        # get process to give us comms
        self.p.get_client_comms.return_value = self.comms
        # tell our controller which blocks the process can talk to
        response = MagicMock(id=self.cc.REMOTE_BLOCKS_ID, value=["blockname"])
        self.cc.put(response)
        # tell our controller the serialized state of the block
        response = MagicMock(id=self.cc.BLOCK_ID, changes=[[[], self.serialized]])
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
        self.assertEqual(list(self.b), [
            'meta', 'state', 'status', 'busy', 'disable', 'reset', 'say_hello'])
        m = self.b["say_hello"]
        self.assertEqual(list(m.takes.elements), ["name", "sleep"])
        self.assertEqual(type(m.takes.elements["name"]), StringMeta)
        self.assertEqual(type(m.takes.elements["sleep"]), NumberMeta)
        self.assertEqual(list(m.returns.elements), ["greeting"])
        self.assertEqual(type(m.returns.elements["greeting"]), StringMeta)
        self.assertEqual(m.defaults, dict(sleep=0))

    def test_call_method(self):
        self.p.create_queue.return_value = queue.Queue()
        def f(request):
            request.respond_with_return(dict(
                greeting="Hello %s" % request.parameters["name"]))
        self.comms.q.put.side_effect = f
        ret = self.b.say_hello(name="me")
        self.assertEqual(ret.greeting, "Hello me")

    def test_put_update_response(self):
        m = MagicMock(spec=Attribute)
        self.b.replace_endpoints(dict(child=m))
        response = MagicMock(
            id=self.cc.BLOCK_ID,
            changes=[[["child", "value"], "change"]])
        self.cc.put(response)
        m.set_value.assert_called_once_with("change", notify=False)

    def test_put_root_update_response(self):
        attr1 = Attribute(StringMeta("dummy"))
        attr2 = Attribute(StringMeta("dummy2"))
        new_block_structure = OrderedDict(typeid='malcolm:core/Block:1.0')
        new_block_structure["attr1"] = attr1.to_dict()
        new_block_structure["attr2"] = attr2.to_dict()
        response = MagicMock(
            id=self.cc.BLOCK_ID,
            changes=[[[], new_block_structure]])
        self.cc.put(response)
        self.assertEqual(self.b.to_dict(), new_block_structure)


if __name__ == "__main__":
    unittest.main(verbosity=2)
