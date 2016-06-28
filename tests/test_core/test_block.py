import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock, call

# module imports
from malcolm.core.block import Block


class TestBlock(unittest.TestCase):

    def test_init(self):
        b = Block("blockname")
        self.assertEqual(b.name, "blockname")
        self.assertEqual(list(b._methods), [])
        self.assertEqual("malcolm:core/Block:1.0", b.typeid)

    def test_add_method_registers(self):
        b = Block("blockname")
        b.on_changed = MagicMock(side_effect=b.on_changed)
        m = MagicMock()
        m.name = "mymethod"
        b.add_method(m)
        self.assertEqual(list(b._methods), ["mymethod"])
        self.assertFalse(m.called)
        b.on_changed.assert_called_with([[m.name], m.to_dict.return_value])
        m.return_value = 42
        self.assertEqual(b.mymethod(), 42)
        m.assert_called_once_with()

    def test_add_attribute(self):
        b = Block("blockname")
        b.on_changed = MagicMock(side_effect=b.on_changed)
        attr = MagicMock()
        attr.name = "attr"
        b.add_attribute(attr)
        attr.set_parent.assert_called_once_with(b)
        self.assertEqual({"attr":attr}, b._attributes)
        self.assertIs(attr, b.attr)
        b.on_changed.assert_called_with(
            [[attr.name], attr.to_dict.return_value])

    def test_lock_released(self):
        b = Block("blockname")
        acquire = MagicMock()
        release = MagicMock()
        lock_methods = MagicMock()
        lock_methods.attach_mock(acquire, "acquire")
        lock_methods.attach_mock(release, "release")
        def enter_side_effect(*args):
            acquire()
        def exit_side_effect(*args):
            release()
        b.lock = MagicMock()
        b.lock.__enter__.side_effect = enter_side_effect
        b.lock.__exit__.side_effect = exit_side_effect

        with b.lock:
            with b.lock_released():
                pass

        self.assertEquals(
            [call.acquire(), call.release(), call.acquire(), call.release()],
            lock_methods.method_calls)

class TestToDict(unittest.TestCase):

    def test_returns_dict(self):
        method_dict = OrderedDict(takes=OrderedDict(one=OrderedDict()),
                                  returns=OrderedDict(one=OrderedDict()),
                                  defaults=OrderedDict())

        m1 = MagicMock()
        m1.name = "method_one"
        m1.to_dict.return_value = method_dict

        m2 = MagicMock()
        m2.name = "method_two"
        m2.to_dict.return_value = method_dict

        a1 = MagicMock()
        a1.name = "attr_one"
        a1dict = OrderedDict(value="test", meta=MagicMock())
        a1.to_dict.return_value = a1dict

        a2 = MagicMock()
        a2.name = "attr_two"
        a2dict = OrderedDict(value="value", meta=MagicMock())
        a2.to_dict.return_value = a2dict

        block = Block("Test")
        block.add_method(m1)
        block.add_method(m2)
        block.add_attribute(a1)
        block.add_attribute(a2)

        m1.reset_mock()
        m2.reset_mock()
        a1.reset_mock()
        a2.reset_mock()

        expected_dict = OrderedDict()
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
        self.block = Block("TestBlock")
        self.block.parent = MagicMock()
        self.method = MagicMock()
        self.method.name = "get_things"
        self.attribute = MagicMock()
        self.attribute.name = "test_attribute"
        self.response = MagicMock()
        self.block.add_method(self.method)
        self.block.add_attribute(self.attribute)

    def test_given_request_then_pass_to_correct_method(self):
        request = MagicMock()
        request.type_ = "Post"
        request.endpoint = ["TestBlock", "device", "get_things"]

        self.block.handle_request(request)

        self.method.get_response.assert_called_once_with(request)
        response = self.method.get_response.return_value
        self.block.parent.block_respond.assert_called_once_with(
            response, request.response_queue)

    def test_given_put_then_update_attribute(self):
        put_value = MagicMock()
        request = MagicMock()
        request.type_ = "Put"
        request.endpoint = ["TestBlock", "test_attribute"]
        request.value = put_value

        self.block.handle_request(request)

        self.attribute.put.assert_called_once_with(put_value)
        self.attribute.set_value.assert_called_once_with(put_value)
        response = self.block.parent.block_respond.call_args[0][0]
        self.assertEqual("Return", response.type_)
        self.assertIsNone(response.value)
        response_queue = self.block.parent.block_respond.call_args[0][1]
        self.assertEqual(request.response_queue, response_queue)

    def test_invalid_request_fails(self):
        request = MagicMock()
        request.type_ = "Get"

        self.assertRaises(AssertionError, self.block.handle_request, request)

if __name__ == "__main__":
    unittest.main(verbosity=2)
