import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# import logging
# logging.basicConfig(level=logging.DEBUG)

import setup_malcolm_paths
from mock import Mock
from threading import RLock

# module imports
from malcolm.compat import OrderedDict
from malcolm.core.notifier import Notifier
from malcolm.core.request import Return, Subscribe, Unsubscribe
from malcolm.core.response import Update, Delta
from malcolm.core.serializable import serialize_object


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

    def to_dict(self):
        return serialize_object(self.data)


class TestNotifier(unittest.TestCase):

    def setUp(self):
        self.lock = RLock()
        self.block = Dummy()
        self.o = Notifier("Notifier", self.lock, self.block)

    def test_subscribe_no_data_then_set_data(self):
        # subscribe
        request = Subscribe(
            path=["b", "attr", "value"], delta=False, callback=Mock())
        self.handle_subscribe(request)
        self.assertEqual(
            self.o._tree.children["attr"].children["value"].requests, [request])
        request.callback.assert_called_once_with(Update(value=None))
        request.callback.reset_mock()
        # set data and check response
        self.block["attr"] = Dummy()
        with self.o.changes_squashed:
            self.block.attr["value"] = 32
            self.o.add_squashed_change(["b", "attr", "value"], 32)
        self.assertEqual(self.block.attr.value, 32)
        request.callback.assert_called_once_with(Update(value=32))
        request.callback.reset_mock()
        # unsubscribe
        self.handle_unsubscribe(Unsubscribe(callback=request.callback))
        request.callback.assert_called_once_with(Return(value=None))
        request.callback.reset_mock()
        # notify and check no longer responding
        with self.o.changes_squashed:
            self.block.attr["value"] = 33
            self.o.add_squashed_change(["b", "attr", "value"], 33)
        self.assertEqual(self.block.attr.value, 33)
        request.callback.assert_not_called()

    def handle_unsubscribe(self, request):
        responses = self.o.handle_unsubscribe(request)
        for cb, response in responses:
            cb(response)

    def handle_subscribe(self, request):
        responses = self.o.handle_subscribe(request)
        for cb, response in responses:
            cb(response)

    def test_2_subscribes(self):
        # set some data
        self.block["attr"] = Dummy()
        self.block.attr["value"] = 32
        # subscribe once and check initial response
        r1 = Subscribe(
            path=["b", "attr", "value"], delta=False, callback=Mock())
        self.handle_subscribe(r1)
        r1.callback.assert_called_once_with(Update(value=32))
        r1.callback.reset_mock()
        # subscribe again and check initial response
        r2 = Subscribe(path=["b"], delta=True, callback=Mock())
        self.handle_subscribe(r2)
        r2.callback.assert_called_once_with(Delta(
            changes=[[[], dict(attr=dict(value=32))]]))
        r2.callback.reset_mock()
        # set some data and check only second got called
        self.block["attr2"] = Dummy()
        with self.o.changes_squashed:
            self.block.attr2["value"] = "st"
            self.o.add_squashed_change(["b", "attr2"], self.block.attr2)
        r1.callback.assert_not_called()
        r2.callback.assert_called_once_with(Delta(
            changes=[[["attr2"], dict(value="st")]]))
        r2.callback.reset_mock()
        # delete the first and check calls
        with self.o.changes_squashed:
            self.block.data.pop("attr")
            self.o.add_squashed_change(["b", "attr"])
        r1.callback.assert_called_once_with(Update(value=None))
        r1.callback.reset_mock()
        r2.callback.assert_called_once_with(Delta(
            changes=[[["attr"]]]))
        r2.callback.reset_mock()
        # add it again and check updates
        self.block["attr"] = Dummy()
        with self.o.changes_squashed:
            self.block.attr["value"] = 22
            self.o.add_squashed_change(["b", "attr"], self.block.attr)
        r1.callback.assert_called_once_with(Update(value=22))
        r2.callback.assert_called_once_with(Delta(
            changes=[[["attr"], dict(value=22)]]))

    def test_update_squashing(self):
        # set some data
        self.block["attr"] = Dummy()
        self.block.attr["value"] = 32
        self.block["attr2"] = Dummy()
        self.block.attr2["value"] = "st"
        # subscribe once and check initial response
        r1 = Subscribe(path=["b"], delta=True, callback=Mock())
        self.handle_subscribe(r1)
        expected = OrderedDict()
        expected["attr"] = dict(value=32)
        expected["attr2"] = dict(value="st")
        r1.callback.assert_called_once_with(Delta(changes=[[[], expected]]))
        r1.callback.reset_mock()
        # squash two changes together
        with self.o.changes_squashed:
            self.block.attr["value"] = 33
            self.o.add_squashed_change(["b", "attr", "value"], 33)
            self.assertEqual(self.block.attr.value, 33)
            self.block.attr2["value"] = "tr"
            self.o.add_squashed_change(["b", "attr2", "value"], "tr")
            self.assertEqual(self.block.attr2.value, "tr")
        r1.callback.assert_called_once_with(Delta(
            changes=[[["attr", "value"], 33], [["attr2", "value"], "tr"]]))



if __name__ == "__main__":
    unittest.main(verbosity=2)
