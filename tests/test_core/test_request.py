import unittest
from mock import MagicMock

from malcolm.core.request import Request, Get, Post, Subscribe, Unsubscribe, Put
from malcolm.core.response import Return, Error, Update, Delta


class TestRequest(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.o = Request(32, self.callback)

    def test_init(self):
        self.assertEqual(self.o.id, 32)
        self.assertEqual(self.o.callback, self.callback)

    def test_respond_with_return(self):
        cb, response = self.o.return_response(value=5)
        assert cb == self.callback
        assert response == Return(id=32, value=5)

    def test_respond_with_error(self):
        cb, response = self.o.error_response(exception=ValueError("Test Error"))
        assert cb == self.callback
        assert response == Error(id=32, message="Test Error")

    def test_setters(self):
        self.o.set_id(123)
        self.assertEquals(123, self.o.id)
        self.o.set_callback(None)
        self.o.callback(888)
        self.callback.assert_not_called()


class TestGet(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.path = ["BL18I:XSPRESS3", "state", "value"]
        self.o = Get(32, self.path, self.callback)

    def test_init(self):
        self.assertEqual(self.o.typeid, "malcolm:core/Get:1.0")
        self.assertEqual(self.o.id, 32)
        self.assertEqual(self.o.callback, self.callback)
        self.assertEqual(self.path, self.o.path)

    def test_setters(self):
        self.o.set_path(["BL18I:XSPRESS3", "state"])
        self.assertEquals(self.o.path, ["BL18I:XSPRESS3", "state"])


class TestPut(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.path = ["BL18I:XSPRESS3", "state", "value"]
        self.value = "5"
        self.o = Put(32, self.path, self.value, self.callback)

    def test_init(self):
        self.assertEqual(self.o.typeid, "malcolm:core/Put:1.0")
        self.assertEqual(self.o.id, 32)
        self.assertEqual(self.o.callback, self.callback)
        self.assertEqual(self.path, self.o.path)
        self.assertEqual(self.value, self.o.value)

    def test_setters(self):
        self.o.set_value("7")
        self.assertEquals(self.o.value, "7")


class TestPost(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.path = ["BL18I:XSPRESS3", "state", "value"]
        self.parameters = dict(arg1=2, arg2=True)
        self.o = Post(32, self.path, self.parameters, self.callback)

    def test_init(self):
        self.assertEqual(self.o.typeid, "malcolm:core/Post:1.0")
        self.assertEqual(self.o.id, 32)
        self.assertEqual(self.o.callback, self.callback)
        self.assertEqual(self.path, self.o.path)
        self.assertEqual(self.parameters, self.o.parameters)

    def test_setters(self):
        self.o.set_parameters(dict(arg1=2, arg2=False))
        self.assertEquals(self.o.parameters, dict(arg1=2, arg2=False))


class TestSubscribe(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.path = ["BL18I:XSPRESS3", "state", "value"]
        self.delta = True
        self.o = Subscribe(32, self.path, self.delta, self.callback)

    def test_init(self):
        self.assertEqual(self.o.typeid, "malcolm:core/Subscribe:1.0")
        self.assertEqual(self.o.id, 32)
        self.assertEqual(self.o.callback, self.callback)
        self.assertEqual(self.path, self.o.path)
        self.assertEqual(self.delta, self.o.delta)

    def test_respond_with_update(self):
        cb, response = self.o.update_response(value=5)
        assert cb == self.callback
        assert response == Update(id=32, value=5)

    def test_respond_with_delta(self):
        changes = [[["path"], "value"]]
        cb, response = self.o.delta_response(changes)
        assert cb == self.callback
        assert response == Delta(id=32, changes=changes)

    def test_setters(self):
        self.o.set_delta(False)
        self.assertFalse(self.o.delta)


class TestUnsubscribe(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.subscribe = Subscribe(32, callback=self.callback)
        self.subscribes = {self.subscribe.generate_key(): self.subscribe}
        self.o = Unsubscribe(32, self.callback)

    def test_init(self):
        self.assertEqual(self.o.typeid, "malcolm:core/Unsubscribe:1.0")
        self.assertEqual(self.o.id, 32)

    def test_keys_same(self):
        self.assertEqual(self.subscribes[self.o.generate_key()], self.subscribe)
