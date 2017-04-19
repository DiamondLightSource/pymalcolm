import os
import sys
import unittest
from collections import OrderedDict
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from mock import Mock

from malcolm.core.meta import Meta


class TestMeta(unittest.TestCase):

    def setUp(self):
        self.o = Meta("desc")
        self.o.notifier.add_squashed_change = Mock(
            wraps=self.o.notifier.add_squashed_change)
        self.o.set_notifier_path(self.o.notifier, ["path"])

    def test_init(self):
        self.assertEqual(self.o.writeable_in, [])

    def test_set_description(self):
        description = "desc2"
        self.assertEqual(self.o.set_description(description), description)
        self.assertEqual(self.o.description, description)
        self.o.notifier.add_squashed_change.assert_called_once_with(
            ["path", "description"], description)

    def test_set_tags(self):
        tags = ("widget:textinput",)
        self.assertEqual(self.o.set_tags(tags), tags)
        self.assertEqual(self.o.tags, tags)
        self.o.notifier.add_squashed_change.assert_called_once_with(
            ["path", "tags"], tags)

    def test_set_writeable(self):
        writeable = True
        self.assertEqual(self.o.set_writeable(writeable), writeable)
        self.assertEqual(self.o.writeable, writeable)
        self.o.notifier.add_squashed_change.assert_called_once_with(
            ["path", "writeable"], writeable)

    def test_set_label(self):
        label = "my label"
        self.assertEqual(self.o.set_label(label), label)
        self.assertEqual(self.o.label, label)
        self.o.notifier.add_squashed_change.assert_called_once_with(
            ["path", "label"], label)


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.serialized = OrderedDict()
        self.serialized["typeid"] = "filled_in_by_subclass"
        self.serialized["description"] = "desc"
        self.serialized["tags"] = ()
        self.serialized["writeable"] = False
        self.serialized["label"] = ""

    def test_to_dict(self):
        m = Meta("desc")
        m.typeid = "filled_in_by_subclass"
        self.assertEqual(m.to_dict(), self.serialized)

if __name__ == "__main__":
    unittest.main(verbosity=2)
