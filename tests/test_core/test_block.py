import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock, call, patch

# module imports
from malcolm.core.block import Block
from malcolm.core.attribute import Attribute
from malcolm.vmetas import StringMeta
from malcolm.core.method import Method
from malcolm.core.request import Post, Put


class TestBlock(unittest.TestCase):

    def test_init(self):
        b = Block()
        self.assertEqual(list(b.methods), [])
        self.assertEqual("malcolm:core/Block:1.0", b.typeid)

    def test_add_method_registers(self):
        b = Block()
        b.on_changed = MagicMock(side_effect=b.on_changed)
        m = MagicMock()
        b.add_method("mymethod", m)
        self.assertEqual(list(b.methods), ["mymethod"])
        self.assertFalse(m.called)
        b.on_changed.assert_called_with([[m.name], m.to_dict.return_value], True)
        m.return_value = 42
        self.assertEqual(b.mymethod(), 42)
        m.assert_called_once_with()

    def test_add_attribute(self):
        b = Block()
        b.name = 'block'
        b.on_changed = MagicMock(side_effect=b.on_changed)
        attr = MagicMock()
        b.add_attribute("attr", attr)
        attr.set_parent.assert_called_once_with(b, "attr")
        self.assertEqual({"attr":attr}, b.attributes)
        self.assertIs(attr, b.attr)
        b.on_changed.assert_called_with(
            [[attr.name], attr.to_dict.return_value], True)

    def test_lock_released(self):
        b = Block()
        b.name = "blockname"
        b.lock.acquire = MagicMock(wrap=b.lock.acquire)
        b.lock.release = MagicMock(wrap=b.lock.release)
        lock_methods = MagicMock()
        lock_methods.attach_mock(b.lock.acquire, "acquire")
        lock_methods.attach_mock(b.lock.release, "release")

        with b.lock:
            with b.lock_released():
                pass

        self.assertEquals(
            [call.acquire(), call.release(), call.acquire(), call.release()],
            lock_methods.method_calls)

    def test_replace_children(self):
        b = Block()
        b.name = "blockname"
        b.methods["m1"] = 2
        b.attributes["a1"] = 3
        setattr(b, "m1", 2)
        setattr(b, "a1", 3)
        attr_meta = StringMeta(description="desc")
        attr = Attribute(attr_meta)
        b.add_attribute('attr', attr)
        method = Method(description="desc")
        b.add_method('method', method)
        b.on_changed = MagicMock(wrap=b.on_changed)
        b.replace_children({'attr':attr, 'method':method})
        self.assertEqual(b.attributes, dict(attr=attr))
        self.assertEqual(b.methods, dict(method=method))
        b.on_changed.assert_called_once_with(
            [[], b.to_dict()], True)
        self.assertFalse(hasattr(b, "m1"))
        self.assertFalse(hasattr(b, "a1"))

    def test_notify(self):
        b = Block()
        b.set_parent(MagicMock(), "n")
        b.notify_subscribers()
        b.parent.notify_subscribers.assert_called_once_with("n")


class TestToDict(unittest.TestCase):

    def test_returns_dict(self):
        method_dict = OrderedDict(takes=OrderedDict(one=OrderedDict()),
                                  returns=OrderedDict(one=OrderedDict()),
                                  defaults=OrderedDict())

        m1 = MagicMock()
        m1.to_dict.return_value = method_dict

        m2 = MagicMock()
        m2.to_dict.return_value = method_dict

        a1 = MagicMock()
        a1dict = OrderedDict(value="test", meta=MagicMock())
        a1.to_dict.return_value = a1dict

        a2 = MagicMock()
        a2dict = OrderedDict(value="value", meta=MagicMock())
        a2.to_dict.return_value = a2dict

        block = Block()
        block.set_parent(MagicMock(), "Test")
        block.add_method('method_one', m1)
        block.add_method('method_two', m2)
        block.add_attribute('attr_one', a1)
        block.add_attribute('attr_two', a2)

        m1.reset_mock()
        m2.reset_mock()
        a1.reset_mock()
        a2.reset_mock()

        expected_dict = OrderedDict()
        expected_dict['typeid'] = "malcolm:core/Block:1.0"
        expected_dict['attr_one'] = a1dict
        expected_dict['attr_two'] = a2dict
        expected_dict['method_one'] = method_dict
        expected_dict['method_two'] = method_dict

        response = block.to_dict()

        m1.to_dict.assert_called_once_with()
        m2.to_dict.assert_called_once_with()
        self.assertEqual(expected_dict, response)


class TestHandleRequest(unittest.TestCase):

    def setUp(self):
        self.block = Block()
        self.block.set_parent(MagicMock(), "TestBlock")
        self.method = MagicMock()
        self.attribute = MagicMock()
        self.response = MagicMock()
        self.block.add_method('get_things', self.method)
        self.block.add_attribute('test_attribute', self.attribute)

    def test_given_request_then_pass_to_correct_method(self):
        endpoint = ["TestBlock", "get_things"]
        request = Post(MagicMock(), MagicMock(), endpoint)

        self.block.handle_request(request)

        self.method.get_response.assert_called_once_with(request)
        response = self.method.get_response.return_value
        self.block.parent.block_respond.assert_called_once_with(
            response, request.response_queue)

    def test_given_put_then_update_attribute(self):
        endpoint = ["TestBlock", "test_attribute", "value"]
        value = "5"
        request = Put(MagicMock(), MagicMock(), endpoint, value)

        self.block.handle_request(request)

        self.attribute.put.assert_called_once_with(value)
        self.attribute.set_value.assert_called_once_with(value)
        response = self.block.parent.block_respond.call_args[0][0]
        self.assertEqual("malcolm:core/Return:1.0", response.typeid)
        self.assertIsNone(response.value)
        response_queue = self.block.parent.block_respond.call_args[0][1]
        self.assertEqual(request.response_queue, response_queue)

    def test_invalid_request_fails(self):
        request = MagicMock()
        request.type_ = "Get"

        self.assertRaises(AssertionError, self.block.handle_request, request)

    def test_invalid_request_fails(self):
        endpoint = ["a","b","c","d"]
        request = Post(MagicMock(), MagicMock(), endpoint)
        self.assertRaises(ValueError, self.block.handle_request, request)

        request = Put(MagicMock(), MagicMock(), endpoint)
        self.assertRaises(ValueError, self.block.handle_request, request)

if __name__ == "__main__":
    unittest.main(verbosity=2)
