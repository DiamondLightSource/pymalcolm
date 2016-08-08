import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from malcolm.core.request import Request, Get, Post, Subscribe, Unsubscribe, Put
from malcolm.core.response import Return, Error, Update, Delta

import unittest
from mock import MagicMock, patch


class TestRequest(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.response_queue = MagicMock()
        self.request = Request(self.context, self.response_queue)

    def test_init(self):
        self.assertEqual(self.context, self.request.context)
        self.assertEqual(self.response_queue, self.request.response_queue)

    def test_repr(self):
        r = Request(MagicMock(), MagicMock())
        s = r.__repr__()
        self.assertTrue(isinstance(s, str))
        self.assertIn('id', s)

    def test_respond_with_return(self):

        self.request.respond_with_return(value=5)

        call_arg = self.response_queue.put.call_args_list[0][0][0].to_dict()

        expected_response = Return(self.request.id, self.request.context, value=5).to_dict()

        self.assertEqual(call_arg, expected_response)

    def test_respond_with_error(self):

        self.request.respond_with_error(message="Test Error")

        call_arg = self.response_queue.put.call_args_list[0][0][0].to_dict()

        expected_response = Error(self.request.id, self.request.context,
                                  message="Test Error").to_dict()

        self.assertEqual(call_arg, expected_response)

    def test_setters(self):
        self.request.set_id(123)
        self.assertEquals(123, self.request.id)


class TestGet(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.response_queue = MagicMock()
        self.endpoint = ["BL18I:XSPRESS3", "state", "value"]
        self.get = Get(self.context, self.response_queue, self.endpoint)

    def test_init(self):
        self.assertEqual(self.context, self.get.context)
        self.assertEqual(self.response_queue, self.get.response_queue)
        self.assertEqual(self.endpoint, self.get.endpoint)
        self.assertEqual("malcolm:core/Get:1.0", self.get.typeid)

    def test_setters(self):
        self.get.set_endpoint(["BL18I:XSPRESS3", "state", "value2"])
        self.assertEquals(["BL18I:XSPRESS3", "state", "value2"], self.get.endpoint)


class TestPut(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.response_queue = MagicMock()
        self.endpoint = ["BL18I:XSPRESS3", "state", "value"]
        self.value = "5"

        self.put = Put(self.context, self.response_queue, self.endpoint, self.value)

    def test_init(self):
        self.assertEqual(self.context, self.put.context)
        self.assertEqual(self.response_queue, self.put.response_queue)
        self.assertEqual(self.endpoint, self.put.endpoint)
        self.assertEqual(self.value, self.put.value)
        self.assertEqual("malcolm:core/Put:1.0", self.put.typeid)

    def test_setters(self):
        self.put.set_endpoint(["BL18I:XSPRESS3", "state", "value2"])
        self.assertEquals(["BL18I:XSPRESS3", "state", "value2"], self.put.endpoint)

        self.put.set_value("7")
        self.assertEquals("7", self.put.value)


class TestPost(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.response_queue = MagicMock()
        self.endpoint = ["BL18I:XSPRESS3", "state", "value"]
        self.parameters = dict(arg1=5, arg2=True)

        self.post = Post(self.context, self.response_queue, self.endpoint, self.parameters)

    def test_init(self):
        self.assertEqual(self.context, self.post.context)
        self.assertEqual(self.response_queue, self.post.response_queue)
        self.assertEqual(self.endpoint, self.post.endpoint)
        self.assertEqual(self.parameters, self.post.parameters)
        self.assertEqual("malcolm:core/Post:1.0", self.post.typeid)

    def test_setters(self):
        self.post.set_endpoint(["BL18I:XSPRESS3", "state", "value2"])
        self.assertEquals(["BL18I:XSPRESS3", "state", "value2"], self.post.endpoint)

        self.post.set_parameters(dict(arg1=2, arg2=False))
        self.assertEquals(dict(arg1=2, arg2=False), self.post.parameters)


class TestSubscribe(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.response_queue = MagicMock()
        self.endpoint = ["BL18I:XSPRESS3", "state", "value"]
        self.delta = True
        self.subscribe = Subscribe(
            self.context, self.response_queue, self.endpoint, delta=self.delta)

    def test_init(self):
        self.assertEqual(self.context, self.subscribe.context)
        self.assertEqual(self.response_queue, self.subscribe.response_queue)
        self.assertEqual(self.endpoint, self.subscribe.endpoint)
        self.assertEqual(self.delta, self.subscribe.delta)
        self.assertEqual("malcolm:core/Subscribe:1.0", self.subscribe.typeid)

    def test_respond_with_update(self):
        value = MagicMock()

        self.subscribe.respond_with_update(value)

        call_arg = self.response_queue.put.call_args_list[0][0][0].to_dict()

        expected_response = Update(self.subscribe.id, self.subscribe.context, value=value).to_dict()

        self.assertEqual(call_arg, expected_response)

    def test_respond_with_delta(self):
        changes = [[["path"], "value"]]

        self.subscribe.respond_with_delta(changes)

        call_arg = self.response_queue.put.call_args_list[0][0][0].to_dict()

        expected_response = Delta(self.subscribe.id, self.subscribe.context, changes=changes).to_dict()

        self.assertEqual(call_arg, expected_response)

    def test_setters(self):
        self.subscribe.set_endpoint(["BL18I:XSPRESS3", "state", "value2"])
        self.assertEquals(["BL18I:XSPRESS3", "state", "value2"], self.subscribe.endpoint)

        self.subscribe.set_delta(False)
        self.assertFalse(self.subscribe.delta)


class TestUnsubscribe(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.response_queue = MagicMock()
        self.unsubscribe = Unsubscribe(self.context, self.response_queue)

    def test_init(self):
        self.assertEqual(self.context, self.unsubscribe.context)
        self.assertEqual(self.response_queue, self.unsubscribe.response_queue)
        self.assertEqual("malcolm:core/Unsubscribe:1.0", self.unsubscribe.typeid)

if __name__ == "__main__":
    unittest.main(verbosity=2)
