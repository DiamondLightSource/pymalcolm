import unittest

from malcolm.core.response import Response, Return, Error, Delta, Update


class TestResponse(unittest.TestCase):

    def test_init(self):
        r = Response(123)
        self.assertEquals(r.id, 123)

    def test_Return(self):
        r = Return(123, "vv")
        self.assertEquals(r.typeid, "malcolm:core/Return:1.0")
        self.assertEquals(r.id, 123)
        self.assertEquals(r.value, "vv")

    def test_Error(self):
        r = Error(123, "Test Error2")
        self.assertEquals(r.typeid, "malcolm:core/Error:1.0")
        self.assertEquals(r.id, 123)
        self.assertEquals(r.message, "Test Error2")

    def test_Update(self):
        r = Update(123, 9)
        self.assertEquals(r.typeid, "malcolm:core/Update:1.0")
        self.assertEquals(r.id, 123)
        self.assertEquals(r.value, 9)

    def test_Delta(self):
        changes = [[["path"], "value"]]
        r = Delta(123, changes)
        self.assertEquals(r.typeid, "malcolm:core/Delta:1.0")
        self.assertEquals(r.id, 123)
        self.assertEquals(r.changes, changes)
