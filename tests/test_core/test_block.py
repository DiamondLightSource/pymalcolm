import unittest
from collections import OrderedDict
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# mock
from pkg_resources import require
require("mock")
from mock import MagicMock, patch

# module imports
from malcolm.core.block import Block


class TestBlock(unittest.TestCase):

    def test_init(self):
        b = Block("blockname")
        self.assertEqual(b.name, "blockname")
        self.assertEqual(b._methods.keys(), [])

    def test_add_method_registers(self):
        b = Block("blockname")
        m = MagicMock()
        m.name = "mymethod"
        b.add_method(m)
        self.assertEqual(b._methods.keys(), ["mymethod"])
        self.assertFalse(m.called)
        m.return_value = 42
        self.assertEqual(b.mymethod(), 42)
        m.assert_called_once_with()


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

        self.meta_map = Block("Test")
        self.meta_map.add_method(m1)
        self.meta_map.add_method(m2)

        expected_methods_dict = OrderedDict()
        expected_methods_dict['method_one'] = method_dict
        expected_methods_dict['method_two'] = method_dict

        expected_dict = OrderedDict()
        expected_dict['methods'] = expected_methods_dict

        response = self.meta_map.to_dict()

        m1.to_dict.assert_called_once_with()
        m2.to_dict.assert_called_once_with()
        self.assertEqual(expected_dict, response)


class TestHandleRequest(unittest.TestCase):

    def setUp(self):
        self.block = Block("TestBlock")
        self.method = MagicMock()
        self.method.name = "get_things"
        self.response = MagicMock()
        self.method.handle_request.return_value = self.response
        self.block.add_method(self.method)

    def test_given_request_then_pass_to_correct_method(self):
        request = MagicMock()
        request.type = "Post"
        request.endpoint = ["TestBlock", "device", "get_things"]

        response = self.block.handle_request(request)

        self.assertEqual(self.response, response)

    def test_given_get_then_return_attribute(self):
        self.block.state = MagicMock()
        self.block.state.value = "Running"
        request = MagicMock()
        request.type = "Get"
        request.endpoint = ["TestBlock", "state", "value"]

        response = self.block.handle_request(request)

        self.assertEqual("Running", response)

    def test_given_get_block_then_return_self(self):
        request = MagicMock()
        request.type = "Get"
        request.endpoint = ["TestBlock"]

        response = self.block.handle_request(request)

        self.assertEqual(self.block, response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
