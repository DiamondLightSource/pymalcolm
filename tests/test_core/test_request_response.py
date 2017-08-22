import unittest
import os
from mock import MagicMock

from malcolm.compat import OrderedDict
from malcolm.core import json_decode
from malcolm.core.request import Request, Get, Post, Subscribe, Unsubscribe, Put
from malcolm.core.response import Return, Error, Update, Delta, Response


def get_doc_json(fname):
    malcolm_root = os.path.join(os.path.dirname(__file__), "..", "..")
    json_root = os.path.join(malcolm_root, "docs", "reference", "json")
    with open(os.path.join(json_root, fname)) as f:
        lines = f.readlines()
    text = "\n".join(lines[1:])
    return json_decode(text)


class TestRequest(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.o = Request(32, self.callback)

    def test_init(self):
        assert self.o.id == 32
        assert self.o.callback == self.callback

    def test_respond_with_return(self):
        cb, response = self.o.return_response(value=5)
        assert cb == self.callback
        assert response == Return(id=32, value=5)

    def test_respond_with_error(self):
        cb, response = self.o.error_response(
            exception=ValueError("Test Error"))
        assert cb == self.callback
        assert response == Error(id=32, message="ValueError: Test Error")

    def test_setters(self):
        self.o.set_id(123)
        assert 123 == self.o.id
        self.o.set_callback(None)
        self.o.callback(888)
        self.callback.assert_not_called()


class TestGet(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.path = ["BL18I:XSPRESS3", "state", "value"]
        self.o = Get(32, self.path, self.callback)

    def test_init(self):
        assert self.o.typeid == "malcolm:core/Get:1.0"
        assert self.o.id == 32
        assert self.o.callback == self.callback
        assert self.path == self.o.path

    def test_setters(self):
        self.o.set_path(["BL18I:XSPRESS3"])
        assert self.o.path == ["BL18I:XSPRESS3"]
        assert get_doc_json("get_xspress3") == self.o.to_dict()

    def test_doc_state(self):
        assert get_doc_json("get_xspress3_state_value") == self.o.to_dict()


class TestPut(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.path = ["BL18I:XSPRESS3:HDF", "filePath", "value"]
        self.value = "/path/to/file.h5"
        self.o = Put(35, self.path, self.value, self.callback)

    def test_init(self):
        assert self.o.typeid == "malcolm:core/Put:1.0"
        assert self.o.id == 35
        assert self.o.callback == self.callback
        assert self.path == self.o.path
        assert self.value == self.o.value

    def test_setters(self):
        self.o.set_value("7")
        assert self.o.value == "7"

    def test_doc(self):
        assert get_doc_json("put_hdf_file_path") == self.o.to_dict()


class TestPost(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.path = ["BL18I:XSPRESS3", "configure"]
        self.parameters = OrderedDict()
        self.parameters["filePath"] = "/path/to/file.h5"
        self.parameters["exposure"] = 0.1
        self.o = Post(2, self.path, self.parameters, self.callback)

    def test_init(self):
        assert self.o.typeid == "malcolm:core/Post:1.0"
        assert self.o.id == 2
        assert self.o.callback == self.callback
        assert self.path == self.o.path
        assert self.parameters == self.o.parameters

    def test_setters(self):
        self.o.set_parameters(dict(arg1=2, arg2=False))
        assert self.o.parameters == dict(arg1=2, arg2=False)

    def test_doc(self):
        assert get_doc_json("post_xspress3_configure") == self.o.to_dict()


class TestSubscribe(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.path = ["BL18I:XSPRESS3"]
        self.delta = True
        self.o = Subscribe(11, self.path, self.delta, self.callback)

    def test_init(self):
        assert self.o.typeid == "malcolm:core/Subscribe:1.0"
        assert self.o.id == 11
        assert self.o.callback == self.callback
        assert self.path == self.o.path
        assert self.delta == self.o.delta

    def test_respond_with_update(self):
        cb, response = self.o.update_response(value=5)
        assert cb == self.callback
        assert response == Update(id=11, value=5)

    def test_respond_with_delta(self):
        changes = [[["path"], "value"]]
        cb, response = self.o.delta_response(changes)
        assert cb == self.callback
        assert response == Delta(id=11, changes=changes)

    def test_setters(self):
        self.o.set_delta(False)
        assert not self.o.delta
        self.o.set_path(["BL18I:XSPRESS3", "state", "value"])
        self.o.set_id(19)
        d = self.o.to_dict()
        del d["delta"]
        assert get_doc_json("subscribe_xspress3_state_value") == d

    def test_doc(self):
        assert get_doc_json("subscribe_xspress3") == self.o.to_dict()


class TestUnsubscribe(unittest.TestCase):

    def setUp(self):
        self.callback = MagicMock()
        self.subscribe = Subscribe(32, callback=self.callback)
        self.subscribes = {self.subscribe.generate_key(): self.subscribe}
        self.o = Unsubscribe(32, self.callback)

    def test_init(self):
        assert self.o.typeid == "malcolm:core/Unsubscribe:1.0"
        assert self.o.id == 32

    def test_keys_same(self):
        assert self.subscribes[self.o.generate_key()] == self.subscribe

    def test_doc(self):
        assert get_doc_json("unsubscribe") == self.o.to_dict()


class TestResponse(unittest.TestCase):
    def test_init(self):
        r = Response(123)
        assert r.id == 123

    def test_Return(self):
        r = Return(35)
        assert r.typeid == "malcolm:core/Return:1.0"
        assert r.id == 35
        assert r.value is None
        assert get_doc_json("return") == r.to_dict()

    def test_Return_value(self):
        r = Return(32, "Running")
        assert r.typeid == "malcolm:core/Return:1.0"
        assert r.id == 32
        assert r.value == "Running"
        assert get_doc_json("return_state_value") == r.to_dict()

    def test_Error(self):
        r = Error(2, "Non-existant block 'foo'")
        assert r.typeid == "malcolm:core/Error:1.0"
        assert r.id == 2
        assert r.message == "Non-existant block 'foo'"
        assert get_doc_json("error") == r.to_dict()

    def test_Update(self):
        r = Update(19, "Running")
        assert r.typeid == "malcolm:core/Update:1.0"
        assert r.id == 19
        assert r.value == "Running"
        assert get_doc_json("update_state_value") == r.to_dict()

    def test_Delta(self):
        changes = [[["state", "value"], "Running"]]
        r = Delta(123, changes)
        assert r.typeid == "malcolm:core/Delta:1.0"
        assert r.id == 123
        assert r.changes == changes


class TestDeltaChanges(unittest.TestCase):
    def test_update_root(self):
        d = dict(a=32)
        r = Delta(changes=[[[], dict(b=3, c=4)]])
        r.apply_changes_to(d)
        assert d == dict(b=3, c=4)

    def test_update_existing_key(self):
        d = dict(a=32)
        r = Delta(changes=[[["a"], 3]])
        r.apply_changes_to(d)
        assert d == dict(a=3)

    def test_update_nonexisting_key(self):
        d = dict(a=32)
        r = Delta(changes=[[["b"], 3]])
        r.apply_changes_to(d)
        assert d == dict(a=32, b=3)

    def test_update_existing_sub_key(self):
        d = dict(c=dict(a=32))
        r = Delta(changes=[[["c", "a"], 3]])
        r.apply_changes_to(d)
        assert d == dict(c=dict(a=3))

    def test_update_nonexisting_sub_key(self):
        d = dict(d=dict(a=32))
        r = Delta(changes=[[["c", "a"], 3]])
        r.apply_changes_to(d)
        assert d == dict(d=dict(a=32), c=dict(a=3))

    def test_update_exist_and_nonexist_sub(self):
        d = dict(d=dict(a=32))
        r = Delta(changes=[[["d", "b", "x"], 3]])
        r.apply_changes_to(d)
        assert d == dict(d=dict(a=32, b=dict(x=3)))

