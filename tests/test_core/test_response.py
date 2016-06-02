import unittest
import sys
import os
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from pkg_resources import require
require("mock")
from mock import Mock

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
        r = Response.Return(123, Mock(), {"key":"value"})
        self.assertEquals({"key":"value"}, r.fields["value"])

    def test_return_response_to_dict(self):
        context = Mock()
        r = Response.Return(123, context)
        expected = OrderedDict()
        expected["id"] = 123
        expected["type"] = "Return"
        expected["value"] = None
        self.assertEquals(expected, r.to_dict())

if __name__ == "__main__":
    unittest.main(verbosity=2)
