import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock, call, patch

# module imports
from malcolm.core import Block, Attribute
from malcolm.core.vmetas import NumberMeta
from malcolm.core.request import Put, Post
from malcolm.core.response import Return, Error


class TestBlock(unittest.TestCase):

    def test_init(self):
        b = Block()
        self.assertEqual(list(b), [])
        self.assertEqual("malcolm:core/Block:1.0", b.typeid)

    def test_getattr(self):
        b = Block()
        a = Attribute(NumberMeta("int32"))
        b.replace_endpoints(dict(a=a))
        def f(meta, value):
            a.set_value(value)
        b.set_writeable_functions(dict(a=f))
        b.a = 32
        self.assertEqual(b.a, 32)

    def test_getattr_raises(self):
        b = Block()
        self.assertRaises(AttributeError, getattr, b, "_does_not_exist")

    def test_handle_put_request(self):
        parent = MagicMock()
        child = MagicMock(spec=Attribute)
        func = MagicMock()
        b = Block()
        b.replace_endpoints({"child":child})
        b.set_writeable_functions({"child":func})
        b.set_parent(parent, "name")
        request = MagicMock(
            spec=Put, id=12345, response_queue=MagicMock(),
            context=MagicMock(), endpoint=["name", "child", "irrelevant"])
        b.handle_request(request)
        calls = parent.block_respond.call_args_list
        self.assertEquals(1, len(calls))
        response = calls[0][0][0]
        self.assertIsInstance(response, Return)
        self.assertEquals(request.id, response.id)
        self.assertEquals(request.context, response.context)
        self.assertEquals(
            child.handle_request.return_value.to_dict(), response.value)
        self.assertEquals(request.response_queue, calls[0][0][1])

    def test_handle_post_request(self):
        parent = MagicMock()
        child = MagicMock(spec=Attribute)
        func = MagicMock()
        b = Block()
        b.replace_endpoints({"child":child})
        b.set_writeable_functions({"child":func})
        b.set_parent(parent, "name")
        request = MagicMock(
            spec=Post, id=12345, response_queue=MagicMock(),
            context=MagicMock(), endpoint=["name", "child", "irrelevant"])
        b.handle_request(request)
        calls = parent.block_respond.call_args_list
        self.assertEquals(1, len(calls))
        response = calls[0][0][0]
        self.assertIsInstance(response, Return)
        self.assertEquals(request.id, response.id)
        self.assertEquals(request.context, response.context)
        self.assertEquals(
            child.handle_request.return_value.to_dict(), response.value)
        self.assertEquals(request.response_queue, calls[0][0][1])

    def test_handle_request_fails(self):
        parent = MagicMock()
        child = MagicMock(spec=Attribute)
        func = MagicMock()
        child.handle_request.side_effect = Exception("Test exception")
        b = Block()
        b.replace_endpoints({"child":child})
        b.set_writeable_functions({"child":func})
        b.set_parent(parent, "name")
        request = MagicMock(
            spec=Put, id=12345, response_queue=MagicMock(),
            context=MagicMock(), endpoint=["name", "child", "irrelevant"])
        b.handle_request(request)
        calls = parent.block_respond.call_args_list
        self.assertEquals(1, len(calls))
        response = calls[0][0][0]
        self.assertIsInstance(response, Error)
        self.assertEquals(request.id, response.id)
        self.assertEquals(request.context, response.context)
        self.assertEquals("Test exception", response.message)
        self.assertEquals(request.response_queue, calls[0][0][1])

if __name__ == "__main__":
    unittest.main(verbosity=2)
