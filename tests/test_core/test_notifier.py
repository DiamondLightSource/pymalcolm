import unittest
from threading import RLock

from annotypes import serialize_object
from mock import Mock

# module imports
from malcolm.compat import OrderedDict
from malcolm.core.notifier import Notifier
from malcolm.core.request import Return, Subscribe, Unsubscribe
from malcolm.core.response import Delta, Update


class Dummy(object):
    def __init__(self):
        self.data = OrderedDict()

    def __getattr__(self, item):
        try:
            return self.data[item]
        except KeyError:
            raise AttributeError(item)

    def __setitem__(self, item, value):
        self.data[item] = value

    def to_dict(self, dict_cls=dict):
        return serialize_object(self.data, dict_cls)


class TestNotifier(unittest.TestCase):
    def setUp(self):
        self.lock = RLock()
        self.block = Dummy()
        self.o = Notifier("Notifier", self.lock, self.block)

    def test_subscribe_no_data_then_set_data(self):
        # subscribe
        request = Subscribe(path=["b", "attr", "value"], delta=False)
        request.set_callback(Mock())
        self.handle_subscribe(request)
        assert (self.o._tree.children["attr"].children["value"].update_requests) == (
            [request]
        )
        self.assert_called_with(request.callback, Update(value=None))
        request.callback.reset_mock()
        # set data and check response
        self.block["attr"] = Dummy()
        with self.o.changes_squashed:
            self.block.attr["value"] = 32
            self.o.add_squashed_change(["b", "attr", "value"], 32)
        assert self.block.attr.value == 32
        self.assert_called_with(request.callback, Update(value=32))
        request.callback.reset_mock()
        # unsubscribe
        unsub = Unsubscribe()
        unsub.set_callback(request.callback)
        self.handle_unsubscribe(unsub)
        self.assert_called_with(request.callback, Return(value=None))
        request.callback.reset_mock()
        # notify and check no longer responding
        with self.o.changes_squashed:
            self.block.attr["value"] = 33
            self.o.add_squashed_change(["b", "attr", "value"], 33)
        assert self.block.attr.value == 33
        request.callback.assert_not_called()

    def handle_unsubscribe(self, request):
        responses = self.o.handle_unsubscribe(request)
        for cb, response in responses:
            cb(response)

    def handle_subscribe(self, request):
        responses = self.o.handle_subscribe(request)
        for cb, response in responses:
            cb(response)

    def assert_called_with(self, func, response):
        assert func.call_count == 1
        assert func.call_args[0][0].to_dict() == response.to_dict()

    def test_2_subscribes(self):
        # set some data
        self.block["attr"] = Dummy()
        self.block.attr["value"] = 32
        # subscribe once and check initial response
        r1 = Subscribe(path=["b", "attr", "value"], delta=False)
        r1.set_callback(Mock())
        self.handle_subscribe(r1)
        self.assert_called_with(r1.callback, Update(value=32))
        r1.callback.reset_mock()
        # subscribe again and check initial response
        r2 = Subscribe(path=["b"], delta=True)
        r2.set_callback(Mock())
        self.handle_subscribe(r2)
        self.assert_called_with(
            r2.callback, Delta(changes=[[[], dict(attr=dict(value=32))]])
        )
        r2.callback.reset_mock()
        # set some data and check only second got called
        self.block["attr2"] = Dummy()
        with self.o.changes_squashed:
            self.block.attr2["value"] = "st"
            self.o.add_squashed_change(["b", "attr2"], self.block.attr2)
        r1.callback.assert_not_called()
        self.assert_called_with(
            r2.callback, Delta(changes=[[["attr2"], dict(value="st")]])
        )
        r2.callback.reset_mock()
        # delete the first and check calls
        with self.o.changes_squashed:
            self.block.data.pop("attr")
            self.o.add_squashed_delete(["b", "attr"])
        self.assert_called_with(r1.callback, Update(value=None))
        r1.callback.reset_mock()
        self.assert_called_with(r2.callback, Delta(changes=[[["attr"]]]))
        r2.callback.reset_mock()
        # add it again and check updates
        self.block["attr"] = Dummy()
        with self.o.changes_squashed:
            self.block.attr["value"] = 22
            self.o.add_squashed_change(["b", "attr"], self.block.attr)
        self.assert_called_with(r1.callback, Update(value=22))
        self.assert_called_with(
            r2.callback, Delta(changes=[[["attr"], dict(value=22)]])
        )

    def test_update_squashing(self):
        # set some data
        self.block["attr"] = Dummy()
        self.block.attr["value"] = 32
        self.block["attr2"] = Dummy()
        self.block.attr2["value"] = "st"
        # subscribe once and check initial response
        r1 = Subscribe(path=["b"], delta=True)
        r1.set_callback(Mock())
        r2 = Subscribe(path=["b"])
        r2.set_callback(Mock())
        self.handle_subscribe(r1)
        self.handle_subscribe(r2)
        expected = OrderedDict()
        expected["attr"] = dict(value=32)
        expected["attr2"] = dict(value="st")
        self.assert_called_with(r1.callback, Delta(changes=[[[], expected]]))
        self.assert_called_with(r2.callback, Update(value=expected))
        r1.callback.reset_mock()
        r2.callback.reset_mock()
        # squash two changes together
        with self.o.changes_squashed:
            self.block.attr["value"] = 33
            self.o.add_squashed_change(["b", "attr", "value"], 33)
            assert self.block.attr.value == 33
            self.block.attr2["value"] = "tr"
            self.o.add_squashed_change(["b", "attr2", "value"], "tr")
            assert self.block.attr2.value == "tr"
        self.assert_called_with(
            r1.callback,
            Delta(changes=[[["attr", "value"], 33], [["attr2", "value"], "tr"]]),
        )
        expected["attr"]["value"] = 33
        expected["attr2"]["value"] = "tr"
        self.assert_called_with(r2.callback, Update(value=expected))
