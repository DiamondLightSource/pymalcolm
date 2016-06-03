import unittest
from collections import OrderedDict
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# mock
from pkg_resources import require
require("mock")
from mock import MagicMock, patch

from malcolm.core.request import Request


class TestRequest(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.context.to_dict()
        self.response_queue = MagicMock()
        self.request = Request(
            1, self.context, self.response_queue, "Put")

    def test_init(self):
        self.assertEqual(1, self.request.id_)
        self.assertEqual(self.context, self.request.context)
        self.assertEqual(self.response_queue, self.request.response_queue)
        self.assertEqual("Put", self.request.type_)

    def test_to_dict(self):
        context_dict = OrderedDict()
        self.context.to_dict.return_value = context_dict

        expected_dict = OrderedDict()
        expected_dict['id'] = 1
        expected_dict['context'] = context_dict
        expected_dict['type'] = "Put"
        parameters = OrderedDict(x=2, y=10)
        expected_dict['parameters'] = parameters

        self.request.fields['parameters'] = parameters
        response = self.request.to_dict()

        self.assertEqual(expected_dict, response)

    @patch("malcolm.core.response.Response.Return")
    def test_respond_with_return(self, return_mock):
        response = MagicMock()
        return_mock.return_value = response

        self.request.respond_with_return(value=5)

        return_mock.assert_called_once_with(self.request.id_, self.request.context, value=5)
        self.response_queue.put.assert_called_once_with(response)

    @patch("malcolm.core.request.Request")
    def test_Get(self, request_mock):
        endpoint = ["BL18I:XSPRESS3", "state", "value"]
        get = Request.Get(2, self.context, self.response_queue, endpoint)

        request_mock.assert_called_once_with(2, self.context, self.response_queue, type_="Get")

    @patch("malcolm.core.request.Request")
    def test_Post(self, request_mock):
        endpoint = ["BL18I:XSPRESS3", "configure"]
        post = Request.Post(2, self.context, self.response_queue, endpoint)

        request_mock.assert_called_once_with(2, self.context, self.response_queue, type_="Post")

    def test_given_valid_attr_then_return(self):
        param_dict = dict(one=7, two=23)
        post = Request.Post(3, self.context, self.response_queue, [""], parameters=param_dict)

        self.assertEqual(param_dict, post.parameters)

    def test_given_invalid_attr_then_raise_error(self):
        param_dict = dict(one=7, two=23)
        post = Request.Post(3, self.context, self.response_queue, [""], parameters=param_dict)

        with self.assertRaises(KeyError):
            post.null
