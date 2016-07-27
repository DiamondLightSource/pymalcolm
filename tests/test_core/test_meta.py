import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from mock import Mock

from malcolm.core.meta import Meta


class TestInit(unittest.TestCase):

    def test_init(self):
        m = Meta("desc")
        self.assertEquals("desc", m.description)

class TestSetters(unittest.TestCase):
    def setUp(self):
        m = Meta("desc")
        m.on_changed = Mock(wrap=m.on_changed)
        self.m = m

    def test_set_description(self):
        m = self.m
        notify = Mock()
        description = "desc2"
        m.set_description(description, notify)
        self.assertEqual(m.description, description)
        m.on_changed.assert_called_once_with(
            [["description"], description], notify)

    def test_set_tags(self):
        m = self.m
        notify = Mock()
        tags = ["widget:textinput"]
        m.set_tags(tags, notify=notify)
        self.assertEquals(tags, m.tags)
        m.on_changed.assert_called_once_with([["tags"], tags], notify)

    def test_notify_default_is_true(self):
        m = self.m
        m.set_description("desc3")
        m.set_tags([])
        self.assertEqual(m.on_changed.call_count, 2)
        calls = m.on_changed.call_args_list
        self.assertTrue(calls[0][0][1])
        self.assertTrue(calls[1][0][1])


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "filled_in_by_subclass"
        self.serialized["description"] = "desc"
        self.serialized["tags"] = []

    def test_to_dict(self):
        m = Meta("desc")
        m.typeid = "filled_in_by_subclass"
        self.assertEqual(m.to_dict(), self.serialized)

    def test_from_dict(self):
        class MyMeta(Meta):
            typeid = "filled_in_by_subclass"
        m = MyMeta.from_dict(self.serialized)
        self.assertEquals(m.description, "desc")
        self.assertEquals(m.tags, [])

if __name__ == "__main__":
    unittest.main(verbosity=2)
