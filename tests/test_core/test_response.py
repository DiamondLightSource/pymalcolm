import unittest
import sys
import os
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from pkg_resources import require
require("mock")
from mock import Mock, MagicMock

from malcolm.core.response import Response


class TestResponse(unittest.TestCase):
    def test_init(self):
        id_ = 123
        type_ = "Return"
        context = Mock()
        r = Response(id_, context, type_)
        self.assertEquals(id_, r.id_)
        self.assertEquals(type_, r.type_)
        self.assertEquals(context, r.context)

    def test_to_dict(self):
        r = Response(123, Mock(), "Return")
        expected = OrderedDict()
        expected["id"] = 123
        expected["type"] = "Return"
        self.assertEquals(expected, r.to_dict())

    def test_return_response(self):
        context = Mock()
        r = Response.Return(123, context)
        self.assertEquals(123, r.id_)
        self.assertEquals("Return", r.type_)
        self.assertEquals(context, r.context)
        self.assertIsNone(r.fields["value"])
        r = Response.Return(123, Mock(), {"key": "value"})
        self.assertEquals({"key": "value"}, r.fields["value"])

    def test_Error(self):
        context = Mock()
        r = Response.Error(123, context, "Test Error")

        self.assertEquals(123, r.id_)
        self.assertEquals("Error", r.type_)
        self.assertEquals(context, r.context)

    def test_return_update(self):
        context = Mock()
        value = {"attribute":"value"}
        r = Response.Update(123, context, value)
        self.assertEquals(123, r.id_)
        self.assertEquals(context, r.context)
        self.assertEquals({"attribute":"value"}, r.fields["value"])

    def test_return_delta(self):
        context = Mock()
        changes = [[["path"], "value"]]
        r = Response.Delta(123, context, changes)
        self.assertEquals(123, r.id_)
        self.assertEquals(context, r.context)
        self.assertEquals(changes, r.fields["changes"])

    def test_return_response_to_dict(self):
        context = Mock()
        r = Response.Return(123, context)
        expected = OrderedDict()
        expected["id"] = 123
        expected["type"] = "Return"
        expected["value"] = None
        self.assertEquals(expected, r.to_dict())

    def test_getattr(self):
        r = Response.Return(22, None, "bar")
        self.assertEquals(r.value, "bar")
        self.assertRaises(KeyError, lambda: r.ffff)

    def test_from_dict(self):
        serialized = {"id": 123, "type": "Return", "extra_1": "abc",
                      "extra_2": {"field": "data"}}
        response = Response.from_dict(serialized)
        self.assertEquals(123, response.id_)
        self.assertEquals("Return", response.type_)
        self.assertEquals("abc", response.fields["extra_1"])
        self.assertEquals({"field": "data"}, response.fields["extra_2"])
        self.assertIsNone(response.context)

    def test_repr(self):
        r = Response(123, Mock(), "mytype")
        s = r.__repr__()
        self.assertTrue(isinstance(s, str))
        self.assertIn("mytype", s)
        self.assertIn("123", s)

if __name__ == "__main__":
    unittest.main(verbosity=2)
