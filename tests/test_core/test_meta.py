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
        m.process = Mock()
        self.m = m

    def test_set_description(self):
        m = self.m
        description = "desc2"
        m.set_description(description)
        self.assertEqual(m.description, description)
        m.process.report_changes.assert_called_once_with(
            [["description"], description])

    def test_set_tags(self):
        m = self.m
        tags = ("widget:textinput",)
        m.set_tags(tags)
        self.assertEquals(tags, m.tags)
        m.process.report_changes.assert_called_once_with([["tags"], tags])

    def test_set_writeable(self):
        meta = self.m
        writeable = True
        meta.set_writeable(writeable)
        self.assertEquals(meta.writeable, writeable)
        meta.process.report_changes.assert_called_once_with(
            [["writeable"], writeable])

    def test_set_label(self):
        meta = self.m
        label = "my label"
        meta.set_label(label)
        self.assertEquals(meta.label, label)
        meta.process.report_changes.assert_called_once_with(
            [["label"], label])


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
