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
from malcolm.core import Notifier, Get, Subscribe, Unsubscribe, Block, serialize_object


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
        self.process = Mock()
        self.process.create_lock.side_effect = lambda: RLock()
        self.block = Dummy()
        self.o = Notifier("Notifier", self.process, self.block)

    def test_init(self):
        self.process.create_lock.assert_called_once_with()

    def test_get_no_data(self):
        request = Mock(Get, path=["b", "attr", "value"])
        self.o.handle_request(request)
        request.respond_with_error.assert_called_once()

    def test_subscribe_no_data_then_set_data(self):
        # subscribe
        request = Mock(Subscribe, path=["b", "attr", "value"], delta=False)
        self.o.handle_request(request)
        self.assertEqual(
            self.o._tree.children["attr"].children["value"].requests, [request])
        request.respond_with_update.assert_called_once_with(None)
        request.reset_mock()
        # set data and check response
        self.block["attr"] = Dummy()
        self.block.attr["value"] = 32
        self.o.notify_change(["attr", "value"], 32)
        request.respond_with_update.assert_called_once_with(32)
        request.reset_mock()
        # unsubscribe
        unsub = Mock(Unsubscribe)
        unsub.generate_key.return_value = request.generate_key()
        self.o.handle_request(unsub)
        request.respond_with_return.assert_called_once_with()
        request.reset_mock()
        # notify and check no longer responding
        self.o.notify_change(["attr", "value"], 33)
        request.respond_with_return.assert_not_called()

    def test_2_subscribes(self):
        # set some data
        self.block["attr"] = Dummy()
        self.block.attr["value"] = 32
        # subscribe once and check initial response
        r1 = Mock(Subscribe, path=("b", "attr", "value"), delta=False)
        self.o.handle_request(r1)
        r1.respond_with_update.assert_called_once_with(32)
        r1.reset_mock()
        # subscribe again and check initial response
        r2 = Mock(Subscribe, path=("b",), delta=True)
        self.o.handle_request(r2)
        r2.respond_with_delta.assert_called_once_with([[[], dict(attr=dict(value=32))]])
        r2.reset_mock()
        # set some data and check only second got called
        self.block["attr2"] = Dummy()
        self.block.attr2["value"] = "st"
        self.o.notify_change(["attr2"],  self.block.attr2)
        r1.assert_not_called()
        r2.respond_with_delta.assert_called_once_with([[["attr2"], dict(value="st")]])
        r2.reset_mock()
        # delete the first and check calls
        self.block.data.pop("attr")
        self.o.notify_change(["attr"])
        r1.respond_with_update.assert_called_once_with(None)
        r1.reset_mock()
        r2.respond_with_delta.assert_called_once_with([[["attr"]]])
        r2.reset_mock()
        # add it again and check updates
        self.block["attr"] = Dummy()
        self.block.attr["value"] = 22
        self.o.notify_change(["attr"],  self.block.attr)
        r1.respond_with_update.assert_called_once_with(22)
        r2.respond_with_delta.assert_called_once_with([[["attr"], dict(value=22)]])

    def test_update_squashing(self):
        # set some data
        self.block["attr"] = Dummy()
        self.block.attr["value"] = 32
        self.block["attr2"] = Dummy()
        self.block.attr2["value"] = "st"
        # subscribe once and check initial response
        r1 = Mock(Subscribe, path=["b"], delta=True)
        self.o.handle_request(r1)
        r1.respond_with_delta.assert_called_once_with(
            [[[], dict(attr=dict(value=32), attr2=dict(value="st"))]])
        r1.reset_mock()
        # squash two changes together
        with self.o.changes_squashed():
            self.block.attr["value"] = 33
            self.o.notify_change(["attr", "value"], 33)
            self.block.attr2["value"] = "tr"
            self.o.notify_change(["attr2", "value"], "tr")
        r1.respond_with_delta.assert_called_once_with(
            [[["attr", "value"], 33], [["attr2", "value"], "tr"]])



if __name__ == "__main__":
    unittest.main(verbosity=2)
