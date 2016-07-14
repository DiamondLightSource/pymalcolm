import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock, MagicMock

from malcolm.core.response import Response, Return, Error, Delta, Update


class TestResponse(unittest.TestCase):

    def test_init(self):
        id_ = 123
        context = Mock()
        r = Response(id_, context)
        self.assertEquals(id_, r.id_)
        self.assertEquals(None, r.typeid)
        self.assertEquals(context, r.context)

    def test_return_response(self):
        context = Mock()
        r = Return(123, context)
        self.assertEquals(123, r.id_)
        self.assertEquals("malcolm:core/Return:1.0", r.typeid)
        self.assertEquals(context, r.context)
        self.assertIsNone(r.value)
        r = Return(123, Mock(), {"key": "value"})
        self.assertEquals({"key": "value"}, r.value)

    def test_Error(self):
        context = Mock()
        r = Error(123, context, "Test Error")

        self.assertEquals(123, r.id_)
        self.assertEquals("malcolm:core/Error:1.0", r.typeid)
        self.assertEquals(context, r.context)

    def test_return_update(self):
        context = Mock()
        value = {"attribute": "value"}
        r = Update(123, context, value)
        self.assertEquals(123, r.id_)
        self.assertEquals(context, r.context)
        self.assertEquals({"attribute": "value"}, r.value)

    def test_return_delta(self):
        context = Mock()
        changes = [[["path"], "value"]]
        r = Delta(123, context, changes)
        self.assertEquals(123, r.id_)
        self.assertEquals(context, r.context)
        self.assertEquals(changes, r.changes)

    def test_repr(self):
        r = Response(123, Mock())
        s = r.__repr__()
        self.assertTrue(isinstance(s, str))
        self.assertIn("123", s)
        self.assertIn("id", s)

if __name__ == "__main__":
    unittest.main(verbosity=2)
