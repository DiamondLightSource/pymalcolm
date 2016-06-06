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
        self.response_queue = MagicMock()
        self.request = Request(self.context, self.response_queue, "Put")

    def test_init(self):
        self.assertEqual(self.context, self.request.context)
        self.assertEqual(self.response_queue, self.request.response_queue)
        self.assertEqual("Put", self.request.type_)

    def test_to_dict(self):
        expected_dict = OrderedDict()
        expected_dict['id'] = 1
        expected_dict['type'] = "Put"
        parameters = OrderedDict(x=2, y=10)
        expected_dict['parameters'] = parameters

        self.request.id_ = 1
        self.request.fields['parameters'] = parameters
        return_dict = self.request.to_dict()

        self.assertEqual(expected_dict, return_dict)

    def test_from_dict(self):
        serialized = {"id": 1, "type": "Put", "extra_1": "abc",
                      "extra_2": {"field": "data"}}
        request = Request.from_dict(serialized)
        self.assertEquals(1, request.id_)
        self.assertEquals("Put", request.type_)
        self.assertEquals("abc", request.fields["extra_1"])
        self.assertEquals({"field": "data"}, request.fields["extra_2"])
        self.assertIsNone(request.context)
        self.assertIsNone(request.response_queue)

    @patch("malcolm.core.response.Response.Return")
    def test_respond_with_return(self, return_mock):
        response = MagicMock()
        return_mock.return_value = response

        self.request.respond_with_return(value=5)

        return_mock.assert_called_once_with(self.request.id_, self.request.context, value=5)
        self.response_queue.put.assert_called_once_with(response)

    @patch("malcolm.core.response.Response.Error")
    def test_respond_with_error(self, return_mock):
        response = MagicMock()
        return_mock.return_value = response

        self.request.respond_with_error(error_message="Test Error")

        return_mock.assert_called_once_with(self.request.id_, self.request.context,
                                            error_message="Test Error")
        self.response_queue.put.assert_called_once_with(response)

    @patch("malcolm.core.request.Request")
    def test_Get(self, request_mock):
        endpoint = ["BL18I:XSPRESS3", "state", "value"]
        get = Request.Get(self.context, self.response_queue, endpoint)

        request_mock.assert_called_once_with(self.context, self.response_queue, type_="Get")

    @patch("malcolm.core.request.Request")
    def test_Post(self, request_mock):
        endpoint = ["BL18I:XSPRESS3", "configure"]
        post = Request.Post(self.context, self.response_queue, endpoint)

        request_mock.assert_called_once_with(self.context, self.response_queue, type_="Post")

    def test_given_valid_attr_then_return(self):
        param_dict = dict(one=7, two=23)
        post = Request.Post(self.context, self.response_queue, [""], parameters=param_dict)

        self.assertEqual(param_dict, post.parameters)

    def test_given_invalid_attr_then_raise_error(self):
        param_dict = dict(one=7, two=23)
        post = Request.Post(self.context, self.response_queue, [""], parameters=param_dict)

        with self.assertRaises(KeyError):
            post.null

if __name__ == "__main__":
    unittest.main(verbosity=2)
