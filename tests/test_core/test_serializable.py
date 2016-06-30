import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock

from malcolm.core.serializable import Serializable

# Register ScalarMeta as a sublcass of itself so we
# can instantiate it for testing purposes.
Serializable.register("serializable:test")(Serializable)

class TestInit(unittest.TestCase):

    def test_init(self):
        s = Serializable("serialize")
        self.assertEqual("serialize", s.name)
        self.assertEqual("serializable:test", s.typeid)

class TestUpdates(unittest.TestCase):

    def test_parent(self):
        parent = Mock()
        parent.name = "parent"
        s = Serializable("serialize")
        s.set_parent(parent)
        self.assertIs(parent, s.parent)
        self.assertEquals("parent.serialize", s._logger_name)

    def test_on_changed(self):
        change = [["test_attr", "test_value"], 12]
        parent = Mock()
        s = Serializable("test_s")
        s.set_parent(parent)
        notify_flag = Mock()
        s.on_changed(change, notify_flag)
        expected = [["test_s", "test_attr", "test_value"], 12]
        parent.on_changed.assert_called_once_with(expected, notify_flag)

    def test_on_change_notify_flag_default(self):
        parent = Mock()
        s = Serializable("test_s")
        s.set_parent(parent)
        change = [[], Mock()]
        s.on_changed(change)
        parent.on_changed.assert_called_once_with(change, True)

    def test_nop_with_no_parent(self):
        change = [["test"], 123]
        s = Serializable("test_s")
        self.assertIsNone(s.parent)
        s.on_changed(change)
        self.assertEquals([["test"], 123], change)

    def test_update_not_implemented(self):
        s = Serializable("test_s")
        self.assertRaises(NotImplementedError, s.update, Mock())

class TestSerialization(unittest.TestCase):

    def test_to_dict(self):
        @Serializable.register("foo:1.0")
        class DummySerializable(Serializable):
            from_dict = Mock()
        s = DummySerializable("name")
        self.assertEquals({"typeid":"foo:1.0"}, s.to_dict())

    def test_from_dict_returns(self):
        @Serializable.register("foo:1.0")
        class DummySerializable(Serializable):
            from_dict = Mock()
        s = DummySerializable("name")

        d = dict(typeid = "foo:1.0")
        deserialized = Serializable.from_dict("me", d)

        s.from_dict.assert_called_once_with("me", d)
        self.assertEqual(s.from_dict.return_value, deserialized)

    def test_from_dict_not_defined_on_subclass_fails(self):
        @Serializable.register("anything")
        class Faulty(Serializable):
            pass
        self.assertRaises(AssertionError, Serializable.from_dict,
                          "me", dict(typeid="anything"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
